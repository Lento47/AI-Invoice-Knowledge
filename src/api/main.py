from __future__ import annotations

from fastapi import FastAPI

from ai_invoice.schemas import PredictiveResult

from .middleware import configure_middleware
from .routers import health, invoices, models
from .routers.invoices import PredictRequest, predict_from_features

app = FastAPI(title="AI Invoice System")
configure_middleware(app)

# Routers:
# - /health/      -> health.router
# - /invoices/*   -> invoices.router (extract, classify, predict, etc.)
# - /models/*     -> models.router (classifier status/train/classify)
app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(models.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Invoice System API"}


@app.post("/predict", response_model=PredictiveResult, tags=["invoices"])
def predict_endpoint(body: PredictRequest) -> PredictiveResult:
    return predict_from_features(body.features)
