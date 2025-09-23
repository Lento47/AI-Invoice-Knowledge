from __future__ import annotations

import logging
import sys

from fastapi import Depends, FastAPI, HTTPException

from ai_invoice.schemas import PredictiveResult
from ai_invoice.service import predict as predict_service

from .license_validator import LicenseClaims, ensure_feature, require_feature_flag
from .middleware import configure_middleware
from .routers import health, invoices, models, predictive
from .routers.invoices import PredictRequest

# Basic stdout logging
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

app = FastAPI(title="AI Invoice System")
configure_middleware(app)

# Routers:
# - /health/      -> health.router
# - /invoices/*   -> invoices.router (extract, classify, predict)
# - /models/*     -> models.router (classifier status/train/classify)
app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(models.router)
app.include_router(predictive.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Invoice System API"}


# Lightweight alias for /invoices/predict using the same schema/response
@app.post("/predict", response_model=PredictiveResult, tags=["invoices"])
def predict_endpoint(
    body: PredictRequest,
    claims: LicenseClaims = Depends(require_feature_flag("predict")),
) -> PredictiveResult:
    ensure_feature(claims, "predict")
    try:
        return predict_service(body.features)
    except ValueError as exc:
        # Mirror behavior in the invoices router for invalid feature payloads
        raise HTTPException(status_code=400, detail=str(exc)) from exc
