from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pandas.errors import EmptyDataError
from pydantic import BaseModel, Field

from ai_invoice.predictive.model import (
    predict_payment_days,
    status as predictive_status_fn,
    train_from_csv_bytes,
)
from ai_invoice.config import settings

router = APIRouter(prefix="/models/predictive", tags=["models"])


class PredictIn(BaseModel):
    amount: float = Field(..., ge=0)
    customer_age_days: int = Field(..., ge=0)
    prior_invoices: int = Field(..., ge=0)
    late_ratio: float = Field(..., ge=0, le=1)
    weekday: int = Field(..., ge=0, le=6)
    month: int = Field(..., ge=1, le=12)


@router.get("/status")
def predictive_status() -> dict:
    return predictive_status_fn()


@router.post("/train")
async def predictive_train(file: UploadFile = File(...)) -> dict:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if settings.max_upload_bytes and len(payload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum size of {settings.max_upload_bytes} bytes.",
        )
    try:
        result = train_from_csv_bytes(payload)
    except EmptyDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/predict")
def predictive_predict(body: PredictIn) -> dict:
    try:
        return predict_payment_days(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
