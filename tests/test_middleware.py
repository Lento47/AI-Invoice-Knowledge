from __future__ import annotations

import logging
import sys
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_invoice.config import settings
from api.middleware import APIKeyAndLoggingMiddleware
from api.routers.invoices import extract_invoice_endpoint


pytestmark = pytest.mark.anyio()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _build_request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/invoices/classify",
        "headers": headers or [],
    }
    return Request(scope)


def _middleware() -> APIKeyAndLoggingMiddleware:
    async def asgi_app(scope, receive, send):  # pragma: no cover - dummy app
        return None

    return APIKeyAndLoggingMiddleware(asgi_app, config=settings)


@pytest.fixture()
def api_key_guard() -> None:
    previous = settings.api_key
    settings.api_key = "test-secret"
    try:
        yield
    finally:
        settings.api_key = previous


async def test_missing_api_key_is_rejected(api_key_guard, caplog: pytest.LogCaptureFixture) -> None:
    middleware = _middleware()
    called = False

    async def call_next(request: Request) -> Response:
        nonlocal called
        called = True
        return Response("ok")

    request = _build_request()
    with caplog.at_level(logging.INFO, logger="ai_invoice.api.middleware"):
        response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    assert not called
    record = caplog.records[-1]
    assert record.status_code == 401


async def test_authorized_request_logs(api_key_guard, caplog: pytest.LogCaptureFixture) -> None:

    async def call_next(request: Request) -> Response:
        return Response("ok", media_type="application/json")

    middleware = _middleware()
    request = _build_request(headers=[(b"x-api-key", b"test-secret")])

    with caplog.at_level(logging.INFO, logger="ai_invoice.api.middleware"):
        response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    log_records = [record for record in caplog.records if record.name == "ai_invoice.api.middleware"]
    assert log_records, "Expected middleware to emit a log entry"
    record = log_records[-1]
    assert record.status_code == 200
    assert record.method == "POST"
    assert record.path == "/invoices/classify"
    assert record.duration >= 0


async def test_extract_invoice_large_file_rejected() -> None:
    previous_limit = settings.max_upload_bytes
    settings.max_upload_bytes = 5

    upload = UploadFile(filename="invoice.pdf", file=BytesIO(b"abcdef"))

    with pytest.raises(HTTPException) as exc:
        await extract_invoice_endpoint(upload)

    settings.max_upload_bytes = previous_limit

    assert exc.value.status_code == 413
    assert "maximum size" in exc.value.detail
