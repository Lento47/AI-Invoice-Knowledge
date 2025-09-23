from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ai_invoice.classify.model import (
    predict_proba_texts,
    status,
    train_from_csv_bytes,
)

router = APIRouter(prefix="/models", tags=["models"])


class ClassifyIn(BaseModel):
    text: str


@router.get("/classifier/status")
def classifier_status():
    return status()


@router.post("/classifier/train")
async def classifier_train(file: UploadFile = File(...)):
    data = await file.read()
    try:
        metrics = train_from_csv_bytes(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "metrics": metrics}


@router.post("/classifier/classify")
def classifier_classify(body: ClassifyIn):
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
