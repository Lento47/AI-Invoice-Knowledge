from __future__ import annotations

import hmac
import logging
import time
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ai_invoice.config import Settings, settings

LOGGER_NAME = "ai_invoice.api.middleware"


def _is_authorized(header_value: str | None, config: Settings) -> bool:
    """Constant-time compare for API key; if no key configured, allow all."""
    if not getattr(config, "api_key", None):
        return True
    if header_value is None:
        return False
    return hmac.compare_digest(config.api_key, header_value)


class APIKeyAndLoggingMiddleware(BaseHTTPMiddleware):
    """Validate API keys (except /health) and record basic request metrics."""

    def __init__(self, app: ASGIApp, *, config: Settings, logger: logging.Logger | None = None) -> None:
        super().__init__(app)
        self.config = config
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        request.state.start_time = start
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        response: Response | None = None
        try:
            # Allow health without auth (both /health and /health/)
            if request.url.path.rstrip("/") != "/health":
                header = request.headers.get("X-API-Key")
                if not _is_authorized(header, self.config):
                    status_code = status.HTTP_401_UNAUTHORIZED
                    response = JSONResponse({"detail": "Unauthorized"}, status_code=status_code)
                    return response

            request.state.api_key_valid = True
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.logger.exception("Unhandled error while processing request")
            raise
        finally:
            end = time.perf_counter()
            duration = end - start
            request.state.end_time = end
            request.state.duration = duration
            log_data: dict[str, Any] = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration": duration,
                "duration_ms": round(duration * 1000, 3),
            }
            self.logger.info(
                "%s %s -> %s in %.3f ms",
                request.method,
                request.url.path,
                status_code,
                duration * 1000,
                extra=log_data,
            )


def require_api_key(request: Request) -> None:
    """Dependency to enforce API key validation for specific routes."""
    # Skip health explicitly
    if request.url.path.rstrip("/") == "/health":
        return
    if not _is_authorized(request.headers.get("X-API-Key"), settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the configured size.

    Uses Content-Length when provided (cheap path); otherwise lets downstream
    framework handle streaming limits.
    """

    def __init__(self, app: ASGIApp, *, max_len: int = 20 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_len = max_len

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_len:
                    raise HTTPException(status_code=413, detail="Payload too large")
            except ValueError:
                # If header is malformed, let the request proceed; FastAPI will handle it.
                pass
        return await call_next(request)


def configure_middleware(app: FastAPI) -> None:
    # API key + timing/logging
    app.add_middleware(APIKeyAndLoggingMiddleware, config=settings)

    # Body size limit (fallback to default if not present in settings)
    max_len = int(getattr(settings, "max_upload_bytes", 20 * 1024 * 1024))
    app.add_middleware(BodyLimitMiddleware, max_len=max_len)

    # CORS
    trusted_origins = getattr(settings, "cors_trusted_origins", [])
    if trusted_origins:
        allow_origins = list(dict.fromkeys(origin.origin for origin in trusted_origins))
        allow_credentials = any(origin.allow_credentials for origin in trusted_origins)
    else:
        allow_origins = ["*"]
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Convenience list for route-level dependency injection if desired:
Dependencies = [Depends(require_api_key)]
