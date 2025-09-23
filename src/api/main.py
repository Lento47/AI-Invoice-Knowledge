import logging
import sys

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ai_invoice.classify.model import predict_proba_texts
from ai_invoice.predictive.model import predict_one
from ai_invoice.schemas import InvoiceExtraction, PredictiveResult
from ai_invoice.service import extract_invoice

from .middleware import configure_middleware
from .routers import invoices, models as models_router, predictive as predictive_router

import numpy as np

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

app = FastAPI(title="AI Invoice System")
configure_middleware(app)
app.include_router(invoices.router)
app.include_router(models_router.router)
app.include_router(predictive_router.router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/extract", response_model=InvoiceExtraction)
async def extract_endpoint(file: UploadFile = File(...)) -> InvoiceExtraction:
    payload = await file.read()
    return extract_invoice(payload)


class ClassifyIn(BaseModel):
    text: str


@app.post("/classify")
def classify_endpoint(body: ClassifyIn) -> dict:
    labels, proba = predict_proba_texts([body.text])
    if hasattr(proba, "shape"):
        idx = int(np.argmax(proba[0]))
        return {
            "label": str(labels[idx]),
            "proba": float(proba[0][idx]),
            "labels": labels,
        }
    return {
        "label": str(labels[0] if labels else "unknown"),
        "proba": 0.0,
        "labels": labels,
    }


class PredictIn(BaseModel):
    amount: float = Field(0, ge=0)
    customer_age_days: int = Field(0, ge=0)
    prior_invoices: int = Field(0, ge=0)
    late_ratio: float = Field(0, ge=0, le=1)
    weekday: int = Field(0, ge=0, le=6)
    month: int = Field(1, ge=1, le=12)


@app.post("/predict", response_model=PredictiveResult)
def predict_endpoint(body: PredictIn) -> PredictiveResult:
    try:
        result = predict_one(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PredictiveResult(**result)
