from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
from .routers import admin, health, invoices, models, predictive, tica
from .routers.invoices import PredictRequest, predict_from_features


handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)


app = FastAPI(title="AI Invoice System")
configure_middleware(app)

_BASE_DIR = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=str(_BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(models.router)
app.include_router(predictive.router)
app.include_router(admin.router)
app.include_router(tica.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Invoice System API"}


@app.get("/admin", response_class=HTMLResponse)
def admin_portal(request: Request) -> HTMLResponse:
    return _TEMPLATES.TemplateResponse(request, "admin.html", {"request": request})


@app.get("/portal", response_class=HTMLResponse)
def invoice_portal(request: Request) -> HTMLResponse:
    """Render the interactive workspace for invoice operations."""

    return _TEMPLATES.TemplateResponse(request, "invoice_portal.html", {"request": request})


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

