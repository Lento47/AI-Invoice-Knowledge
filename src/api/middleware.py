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
    if not config.api_key:
        return True
    if header_value is None:
        return False
    return hmac.compare_digest(config.api_key, header_value)


class APIKeyAndLoggingMiddleware(BaseHTTPMiddleware):
    """Validate API keys and record basic request metrics."""

    def __init__(self, app: ASGIApp, *, config: Settings, logger: logging.Logger | None = None) -> None:
        super().__init__(app)
        self.config = config
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        request.state.start_time = start
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        response: Response | None = None
        try:
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
            request.state.end_time = end
            duration = end - start
            request.state.duration = duration
            log_data: dict[str, Any] = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration": duration,
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

    if not _is_authorized(request.headers.get("X-API-Key"), settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(APIKeyAndLoggingMiddleware, config=settings)


Dependencies = [Depends(require_api_key)]
