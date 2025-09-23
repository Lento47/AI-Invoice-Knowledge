from __future__ import annotations

import logging
import sys

from fastapi import FastAPI, HTTPException

from ai_invoice.schemas import PredictiveResult

from .middleware import configure_middleware
from .routers import health, invoices, models, predictive
from .routers.invoices import PredictRequest, predict_from_features

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
def predict_endpoint(body: PredictRequest) -> PredictiveResult:
    try:
        return predict_from_features(body.features)
    except ValueError as exc:
        # Mirror behavior in the invoices router for invalid feature payloads
        raise HTTPException(status_code=400, detail=str(exc)) from exc
