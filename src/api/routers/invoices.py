from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ai_invoice.schemas import ClassificationResult, InvoiceExtraction, PredictiveResult
from ai_invoice.service import classify_text, extract_invoice, predict
from ..license_validator import LicenseClaims, ensure_feature, require_feature_flag
from ..middleware import Dependencies
from ai_invoice.config import settings

router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=Dependencies)


class ClassifyRequest(BaseModel):
    text: str


class PredictRequest(BaseModel):
    features: dict


def _validate_and_predict(features: dict) -> PredictiveResult:
    if not features:
        raise HTTPException(status_code=400, detail="features must not be empty.")
    if settings.max_feature_fields and len(features) > settings.max_feature_fields:
        raise HTTPException(
            status_code=413,
            detail=f"Too many feature fields (max {settings.max_feature_fields}).",
        )
    if settings.max_json_body_bytes is not None:
        encoded = json.dumps(features).encode("utf-8")
        if len(encoded) > settings.max_json_body_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Feature payload exceeds maximum size of "
                    f"{settings.max_json_body_bytes} bytes."
                ),
            )
    try:
        return predict(features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Exported helper used by /predict alias in api.main
def predict_from_features(features: dict) -> PredictiveResult:
    return _validate_and_predict(features)


@router.post("/extract", response_model=InvoiceExtraction)
async def extract_invoice_endpoint(
    file: UploadFile = File(...),
    claims: LicenseClaims = Depends(require_feature_flag("extract")),
) -> InvoiceExtraction:
    ensure_feature(claims, "extract")
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if settings.max_upload_bytes and len(payload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum size of {settings.max_upload_bytes} bytes.",
        )
    return extract_invoice(payload)


@router.post("/classify", response_model=ClassificationResult)
def classify_invoice_endpoint(
    body: ClassifyRequest,
    claims: LicenseClaims = Depends(require_feature_flag("classify")),
) -> ClassificationResult:
    ensure_feature(claims, "classify")
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty.")
    if settings.max_text_length and len(body.text) > settings.max_text_length:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds maximum length of {settings.max_text_length} characters.",
        )
    return classify_text(body.text)


@router.post("/predict", response_model=PredictiveResult)
def predict_invoice_endpoint(
    body: PredictRequest,
    claims: LicenseClaims = Depends(require_feature_flag("predict")),
) -> PredictiveResult:
    ensure_feature(claims, "predict")
    return _validate_and_predict(body.features)
