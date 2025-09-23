from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ai_invoice.schemas import ClassificationResult, InvoiceExtraction, PredictiveResult
from ai_invoice.service import classify_text, extract_invoice, predict

router = APIRouter(prefix="/invoices", tags=["invoices"])


class ClassifyRequest(BaseModel):
    text: str


class PredictRequest(BaseModel):
    features: dict


@router.post("/extract", response_model=InvoiceExtraction)
async def extract_invoice_endpoint(file: UploadFile = File(...)) -> InvoiceExtraction:
    payload = await file.read()
    return extract_invoice(payload)


@router.post("/classify", response_model=ClassificationResult)
def classify_invoice_endpoint(body: ClassifyRequest) -> ClassificationResult:
    return classify_text(body.text)


@router.post("/predict", response_model=PredictiveResult)
def predict_invoice_endpoint(body: PredictRequest) -> PredictiveResult:
    try:
        return predict(body.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
