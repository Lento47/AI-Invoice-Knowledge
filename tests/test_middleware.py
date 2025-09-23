from __future__ import annotations

import logging
import os
import sys
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("API_KEY", "test-secret")

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


@pytest.fixture()
def rate_limit_guard() -> None:
    previous_rate = settings.rate_limit_per_minute
    previous_burst = getattr(settings, "rate_limit_burst", None)
    settings.rate_limit_per_minute = None
    settings.rate_limit_burst = None
    try:
        yield
    finally:
        settings.rate_limit_per_minute = previous_rate
        settings.rate_limit_burst = previous_burst


async def test_missing_api_key_is_rejected(
    api_key_guard, rate_limit_guard, caplog: pytest.LogCaptureFixture
) -> None:
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


async def test_authorized_request_logs(
    api_key_guard, rate_limit_guard, caplog: pytest.LogCaptureFixture
) -> None:

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


async def test_rate_limit_allows_within_budget(
    api_key_guard, rate_limit_guard
) -> None:
    settings.rate_limit_per_minute = 2
    settings.rate_limit_burst = 0
    middleware = _middleware()

    async def call_next(request: Request) -> Response:
        return Response("ok")

    request = _build_request(headers=[(b"x-api-key", b"test-secret")])
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200


async def test_rate_limit_throttles_requests(
    api_key_guard, rate_limit_guard, caplog: pytest.LogCaptureFixture
) -> None:
    settings.rate_limit_per_minute = 2
    settings.rate_limit_burst = 0
    middleware = _middleware()

    call_count = 0

    async def call_next(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        return Response("ok")

    headers = [(b"x-api-key", b"test-secret")]
    requests = [_build_request(headers=headers) for _ in range(3)]

    with caplog.at_level(logging.INFO, logger="ai_invoice.api.middleware"):
        responses = [await middleware.dispatch(req, call_next) for req in requests]

    assert [resp.status_code for resp in responses] == [200, 200, 429]
    assert call_count == 2

    throttle_logs = [
        record
        for record in caplog.records
        if record.name == "ai_invoice.api.middleware" and getattr(record, "event", "") == "rate_limit_exceeded"
    ]
    assert throttle_logs, "Expected a throttling log entry"
    throttled_info = [
        record
        for record in caplog.records
        if record.name == "ai_invoice.api.middleware" and getattr(record, "throttled", False)
    ]
    assert throttled_info, "Expected final log entry to mark throttled requests"


async def test_rate_limit_disabled_when_unset(
    api_key_guard, rate_limit_guard
) -> None:
    settings.rate_limit_per_minute = None
    middleware = _middleware()

    call_count = 0

    async def call_next(request: Request) -> Response:
        nonlocal call_count
        call_count += 1
        return Response("ok")

    headers = [(b"x-api-key", b"test-secret")]
    requests = [_build_request(headers=headers) for _ in range(5)]

    responses = [await middleware.dispatch(req, call_next) for req in requests]

    assert all(resp.status_code == 200 for resp in responses)
    assert call_count == len(requests)


async def test_extract_invoice_large_file_rejected() -> None:
    previous_limit = settings.max_upload_bytes
    settings.max_upload_bytes = 5

    upload = UploadFile(filename="invoice.pdf", file=BytesIO(b"abcdef"))

    with pytest.raises(HTTPException) as exc:
        await extract_invoice_endpoint(upload)

    settings.max_upload_bytes = previous_limit

    assert exc.value.status_code == 413
    assert "maximum size" in exc.value.detail
