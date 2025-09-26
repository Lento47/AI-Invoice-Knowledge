from __future__ import annotations

import numpy as np

from .classify.model import predict_proba_texts
from .nlp_extract.parser import parse_structured
from .ocr.engine import run_ocr
from .predictive.model import predict_payment_days
from .schemas import ClassificationResult, InvoiceExtraction, PredictiveResult


def extract_invoice(file_bytes: bytes) -> InvoiceExtraction:
    ocr_result = run_ocr(file_bytes)
    extraction = parse_structured(ocr_result.text, ocr_confidence=ocr_result.average_confidence)
    extraction.raw_text = ocr_result.text
    return extraction


def classify_text(raw_text: str) -> ClassificationResult:
    labels, proba = predict_proba_texts([raw_text])
    if hasattr(proba, "shape"):
        idx = int(np.argmax(proba[0]))
        return ClassificationResult(label=str(labels[idx]), proba=float(proba[0][idx]))
    idx = int(np.argmax(proba))
    return ClassificationResult(label=str(labels[idx]), proba=0.0)


def predict(features: dict) -> PredictiveResult:
    result = predict_payment_days(features)
    return PredictiveResult(**result)
