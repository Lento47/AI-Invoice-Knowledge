from __future__ import annotations

import logging
import sys

from fastapi import Depends, FastAPI, HTTPException

from ai_invoice.schemas import PredictiveResult


STARTUP_LOGGER = logging.getLogger("ai_invoice.api.startup")


try:
    from ai_invoice.config import settings
except ValueError as exc:
    STARTUP_LOGGER.fatal("Invalid configuration detected during startup: %s", exc)
    raise SystemExit(1) from exc


if not settings.api_key and not getattr(settings, "allow_anonymous", False):
    STARTUP_LOGGER.fatal(
        "API_KEY environment variable must be set unless ALLOW_ANONYMOUS=true. Aborting startup."
    )
    raise SystemExit(1)


from .license_validator import LicenseClaims, ensure_feature, require_feature_flag
from .middleware import configure_middleware
from .routers import health, invoices, models, predictive
from .routers.invoices import PredictRequest, predict_from_features


handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)


app = FastAPI(title="AI Invoice System")
configure_middleware(app)

app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(models.router)
app.include_router(predictive.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Invoice System API"}


@app.post("/predict", response_model=PredictiveResult, tags=["invoices"])
def predict_endpoint(
    body: PredictRequest,
    claims: LicenseClaims = Depends(require_feature_flag("predict")),
) -> PredictiveResult:
    ensure_feature(claims, "predict")
    try:
        return predict_from_features(body.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

