from __future__ import annotations

import logging
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

API_KEY = os.getenv("AI_API_KEY")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Require a matching API key on every request except health."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Allow both /health and /health/ without auth
        if request.url.path.rstrip("/") == "/health":
            return await call_next(request)

        if API_KEY:
            key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
            if key != API_KEY:
                raise HTTPException(status_code=401, detail="Invalid API key")

        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Log basic request timing information and append a response header."""

    def __init__(self, app: FastAPI, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(app)
        self._logger = logger or logging.getLogger("ai.api")

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        self._logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"
        return response


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the configured size."""

    def __init__(self, app: FastAPI, max_len: int = 20 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_len = max_len

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        declared = request.headers.get("content-length")
        if declared is not None and int(declared) > self.max_len:
            raise HTTPException(status_code=413, detail="Payload too large")
        return await call_next(request)


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
