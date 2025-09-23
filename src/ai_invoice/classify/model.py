from __future__ import annotations

import io
import os
from typing import Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ai_invoice.config import settings
from .featurize import build_vectorizer

MODEL_PATH = settings.classifier_path


# ---------- Load/Save ----------
def load_or_init() -> Pipeline:
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    pipeline = Pipeline(
        [
            ("tfidf", build_vectorizer()),
            ("clf", LogisticRegression(max_iter=500, solver="lbfgs")),
        ]
    )
    # Provide default label order for untrained model
    pipeline.classes_ = np.array(["invoice", "receipt"])
    return pipeline


def save_model(pipeline: Pipeline) -> None:
    directory = os.path.dirname(MODEL_PATH) or "."
    os.makedirs(directory, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)


# ---------- Predict ----------
def predict_proba_texts(texts: Sequence[str]):
    model = load_or_init()
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(texts)
        labels = list(getattr(model, "classes_", []))
        return labels, proba
    scores = model.decision_function(texts)
    return list(getattr(model, "classes_", [])), scores


# ---------- Train from CSV ----------
def train_from_csv_bytes(
    csv_bytes: bytes, test_size: float = 0.15, random_state: int = 42
) -> dict:
    frame = pd.read_csv(io.BytesIO(csv_bytes))
    if not {"text", "label"}.issubset(frame.columns):
        raise ValueError("CSV must include columns: text,label")

    frame = frame.dropna(subset=["text", "label"]).reset_index(drop=True)
    if len(frame) < 20:
        raise ValueError("Training set too small; need at least 20 rows.")
    if frame["label"].nunique() < 2:
        raise ValueError("Training data must contain at least two labels.")

    X_train, X_test, y_train, y_test = train_test_split(
        frame["text"].astype(str),
        frame["label"].astype(str),
        test_size=test_size,
        random_state=random_state,
        stratify=frame["label"].astype(str),
    )

    pipeline = Pipeline(
        [
            ("tfidf", build_vectorizer()),
            ("clf", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]
    )

    pipeline.fit(X_train, y_train)
    save_model(pipeline)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test) if hasattr(pipeline, "predict_proba") else None

    metrics: dict[str, object] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro")),
        "labels": list(pipeline.classes_),
        "report": classification_report(y_test, y_pred, output_dict=True),
        "count_train": int(len(X_train)),
        "count_test": int(len(X_test)),
    }

    if y_proba is not None:
        top1 = np.max(y_proba, axis=1)
        metrics["avg_confidence_test"] = float(np.mean(top1))

    return metrics


def status() -> dict:
    present = os.path.exists(MODEL_PATH)
    labels: list[str] = []
    if present:
        pipeline: Pipeline = joblib.load(MODEL_PATH)
        labels = list(getattr(pipeline, "classes_", []))
    return {"present": present, "path": MODEL_PATH, "labels": labels}
