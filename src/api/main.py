from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
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
_TEMPLATE_DIR = _BASE_DIR / "templates"
_STATIC_DIR = _BASE_DIR / "static"
_CONSOLE_STATIC_DIR = _STATIC_DIR / "console"
_CONSOLE_INDEX = _CONSOLE_STATIC_DIR / "index.html"

_TEMPLATES = Jinja2Templates(directory=str(_TEMPLATE_DIR))

_STATIC_FILES: StaticFiles | None
# Resolve static files location with a directory-first strategy and a safe package fallback.
_STATIC_FILES = None

if _STATIC_DIR.is_dir():
    _STATIC_FILES = StaticFiles(directory=str(_STATIC_DIR))
else:
    try:
        pkg = (__package__ or "api")  # ← change "api" to your actual package name if you renamed it
        _STATIC_FILES = StaticFiles(packages=[pkg])
    except RuntimeError as exc:  # pragma: no cover - depends on packaging environment
        STARTUP_LOGGER.warning("Static assets unavailable (pkg=%s): %s", pkg, exc)

if _STATIC_FILES is not None:
    app.mount("/static", _STATIC_FILES, name="static")
else:  # pragma: no cover - only exercised when static assets are missing
    STARTUP_LOGGER.warning("Continuing without /static mount; static assets not found")

if _CONSOLE_INDEX.is_file():
    app.mount(
        "/portal",
        StaticFiles(directory=str(_CONSOLE_STATIC_DIR), html=True),
        name="react-portal",
    )

    @app.get("/portal", include_in_schema=False)
    def react_portal_root() -> FileResponse:  # pragma: no cover - simple file response
        """Serve the compiled React console entry point."""

        return FileResponse(_CONSOLE_INDEX)
else:
    STARTUP_LOGGER.info("React console build not found; serving legacy portal at /portal")

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


if not _CONSOLE_INDEX.is_file():

    @app.get("/portal", response_class=HTMLResponse)
    def invoice_portal(request: Request) -> HTMLResponse:
        """Render the interactive workspace for invoice operations."""

        return _TEMPLATES.TemplateResponse(request, "invoice_portal.html", {"request": request})


@app.get("/portal/legacy", response_class=HTMLResponse)
def invoice_portal_legacy(request: Request) -> HTMLResponse:
    """Expose the prior Jinja portal for backwards compatibility."""

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

