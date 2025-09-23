from __future__ import annotations

import os
from typing import Sequence

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ai_invoice.config import settings

from .featurize import build_vectorizer


def load_or_init() -> Pipeline:
    path = settings.classifier_path
    if os.path.exists(path):
        return joblib.load(path)
    pipeline = Pipeline([
        ("vec", build_vectorizer()),
        ("clf", LogisticRegression(max_iter=200)),
    ])
    pipeline.classes_ = np.array(["invoice", "receipt"])
    return pipeline


def predict_proba_texts(texts: Sequence[str]):
    model = load_or_init()
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(texts)
        labels = list(getattr(model, "classes_", []))
        return labels, proba
    scores = model.decision_function(texts)
    return list(getattr(model, "classes_", [])), scores
