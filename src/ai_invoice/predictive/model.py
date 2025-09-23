from __future__ import annotations

import io
import os
from datetime import datetime, timedelta
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ai_invoice.config import settings

from .features import ALL_FEATURE_COLUMNS, REQUIRED_COLUMNS, build_features

MODEL_PATH = settings.predictive_path


def load_or_init() -> Pipeline:
    if os.path.exists(MODEL_PATH):
        model: Pipeline = joblib.load(MODEL_PATH)
        if not hasattr(model, "feature_columns"):
            model.feature_columns = list(ALL_FEATURE_COLUMNS)
        if not hasattr(model, "confidence_proxy_"):
            model.confidence_proxy_ = 0.5
        return model

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("reg", Ridge(alpha=1.0)),
        ]
    )
    pipeline.feature_columns = list(ALL_FEATURE_COLUMNS)
    pipeline.confidence_proxy_ = 0.3
    return pipeline


def save_model(pipe: Pipeline) -> None:
    os.makedirs(os.path.dirname(MODEL_PATH) or ".", exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)


def status() -> dict[str, Any]:
    present = os.path.exists(MODEL_PATH)
    info: dict[str, Any] = {"present": present, "path": MODEL_PATH}
    if present:
        model = load_or_init()
        info["confidence"] = float(getattr(model, "confidence_proxy_", 0.5))
    return info


def _prepare_target(df: pd.DataFrame) -> pd.Series:
    target = pd.to_numeric(df["actual_payment_days"], errors="coerce")
    return target


def _derive_target(df: pd.DataFrame) -> pd.DataFrame:
    if {"issue_date", "paid_date"}.issubset(df.columns):
        issue = pd.to_datetime(df["issue_date"], errors="coerce")
        paid = pd.to_datetime(df["paid_date"], errors="coerce")
        df["actual_payment_days"] = (paid - issue).dt.days
    return df


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = _derive_target(df)
    if "actual_payment_days" not in df.columns:
        raise ValueError(
            "CSV must include actual_payment_days or issue_date and paid_date columns."
        )

    if "weekday" not in df.columns and "issue_date" in df.columns:
        df["weekday"] = pd.to_datetime(df["issue_date"], errors="coerce").dt.weekday
    if "month" not in df.columns and "issue_date" in df.columns:
        df["month"] = pd.to_datetime(df["issue_date"], errors="coerce").dt.month

    df = df.dropna(subset=["actual_payment_days"])
    target = _prepare_target(df)
    df = df.loc[target.notna()].copy()
    df["actual_payment_days"] = target.loc[df.index]
    df = df[df["actual_payment_days"] >= 0]

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "CSV missing required feature columns: "
            + ", ".join(sorted(missing))
        )

    for column in REQUIRED_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=list(REQUIRED_COLUMNS))

    return df


def train_from_csv_bytes(
    csv_bytes: bytes,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    frame = pd.read_csv(io.BytesIO(csv_bytes))
    if frame.empty:
        raise ValueError("Training CSV is empty.")

    frame = _clean_dataframe(frame)

    if len(frame) < 20:
        raise ValueError("Training set too small; need at least 20 rows.")

    features = frame[list(REQUIRED_COLUMNS)].copy()
    target = frame["actual_payment_days"].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
    )

    if len(X_test) == 0:
        raise ValueError("Not enough rows to create a validation split.")

    X_train_features = build_features(X_train)
    X_test_features = build_features(X_test)

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("reg", Ridge(alpha=1.0)),
        ]
    )
    pipeline.fit(X_train_features, y_train)

    predictions = pipeline.predict(X_test_features)
    mae = float(mean_absolute_error(y_test, predictions))
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    r2 = float(r2_score(y_test, predictions))
    confidence_proxy = float(np.clip(1.0 / (1.0 + mae / 15.0), 0.05, 0.95))

    pipeline.feature_columns = list(X_train_features.columns)
    pipeline.confidence_proxy_ = confidence_proxy
    pipeline.training_metrics_ = {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "confidence_proxy": confidence_proxy,
    }

    save_model(pipeline)

    return {
        "count_train": int(len(X_train)),
        "count_test": int(len(X_test)),
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "confidence_proxy": confidence_proxy,
        },
    }


def predict_payment_days(feature_row: dict[str, Any]) -> dict[str, float | str]:
    model = load_or_init()

    try:
        feature_frame = build_features(pd.DataFrame([feature_row]))
    except ValueError as exc:
        raise ValueError(f"Invalid predictive features: {exc}") from exc
    columns = getattr(model, "feature_columns", list(ALL_FEATURE_COLUMNS))
    feature_frame = feature_frame.reindex(columns=columns, fill_value=0.0)

    try:
        prediction = float(model.predict(feature_frame)[0])
        confidence = float(getattr(model, "confidence_proxy_", 0.5))
    except NotFittedError:
        prediction = 30.0
        confidence = float(getattr(model, "confidence_proxy_", 0.3))

    days = float(np.clip(prediction, 0.0, 120.0))
    risk = float(np.clip((days - 30.0) / 60.0, 0.0, 1.0))
    pay_date = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
    confidence = float(np.clip(confidence, 0.05, 0.95))

    return {
        "predicted_payment_days": days,
        "predicted_payment_date": pay_date,
        "risk_score": risk,
        "confidence": confidence,
    }
