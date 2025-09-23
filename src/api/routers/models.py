from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ai_invoice.classify.model import (
    predict_proba_texts,
    status,
    train_from_csv_bytes,
)
from ai_invoice.config import settings
from ..license_validator import LicenseClaims, ensure_feature, require_feature_flag
from ..middleware import Dependencies

router = APIRouter(prefix="/models", tags=["models"], dependencies=Dependencies)


class ClassifyIn(BaseModel):
    text: str


@router.get("/classifier/status")
def classifier_status(
    claims: LicenseClaims = Depends(require_feature_flag("classify")),
):
    ensure_feature(claims, "classify")
    return status()


@router.post("/classifier/train")
async def classifier_train(
    file: UploadFile = File(...),
    claims: LicenseClaims = Depends(require_feature_flag("train")),
):
    ensure_feature(claims, "train")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if settings.max_upload_bytes and len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum size of {settings.max_upload_bytes} bytes.",
        )
    try:
        metrics = train_from_csv_bytes(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "metrics": metrics}


@router.post("/classifier/classify")
def classifier_classify(
    body: ClassifyIn,
    claims: LicenseClaims = Depends(require_feature_flag("classify")),
):
    ensure_feature(claims, "classify")
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty.")
    if settings.max_text_length and len(body.text) > settings.max_text_length:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds maximum length of {settings.max_text_length} characters.",
        )
    labels, proba = predict_proba_texts([body.text])
    if hasattr(proba, "shape"):
        import numpy as np  # local to avoid global dependency elsewhere

        idx = int(np.argmax(proba[0]))
        return {
            "label": str(labels[idx]),
            "proba": float(proba[0][idx]),
            "labels": labels,
        }
    # Fallback for models without predict_proba / decision_function shape
    return {
        "label": str(labels[0] if labels else "unknown"),
        "proba": 0.0,
        "labels": labels,
    }
