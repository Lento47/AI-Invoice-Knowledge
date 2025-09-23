from __future__ import annotations

import os
from datetime import datetime, timedelta

import joblib
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ai_invoice.config import settings

from .features import build_features


def load_or_init() -> Pipeline:
    path = settings.predictive_path
    if os.path.exists(path):
        return joblib.load(path)
    return Pipeline([
        ("scaler", StandardScaler()),
        ("reg", Ridge(alpha=1.0)),
    ])


def predict_payment_days(feature_row: dict) -> dict:
    model = load_or_init()
    features = build_features(pd.DataFrame([feature_row]))
    if hasattr(model, "predict"):
        prediction = float(model.predict(features)[0])
    else:
        prediction = 30.0
    days = float(max(0.0, min(120.0, prediction)))
    risk = float(min(1.0, max(0.0, (days - 30) / 60)))
    pay_date = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
    return {
        "predicted_payment_days": days,
        "predicted_payment_date": pay_date,
        "risk_score": risk,
        "confidence": 0.5,
    }
