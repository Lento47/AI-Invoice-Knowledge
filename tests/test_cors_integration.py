from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Iterable

import pytest
from fastapi import FastAPI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from api.middleware import configure_middleware
from ai_invoice.config import TrustedCORSOrigin, settings


@pytest.fixture
def anyio_backend() -> str:
    """Run anyio-powered tests on asyncio to avoid optional dependencies."""

    return "asyncio"


@contextmanager
def configure_cors_app(origins: Iterable[TrustedCORSOrigin]):
    """Configure middleware for a temporary FastAPI application."""

    previous = settings.cors_trusted_origins
    settings.cors_trusted_origins = list(origins)
    app = FastAPI()
    configure_middleware(app)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    try:
        yield app
    finally:
        settings.cors_trusted_origins = previous


def _encode_headers(headers: Iterable[tuple[str, str]]) -> list[tuple[bytes, bytes]]:
    return [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in headers
    ]


def _decode_headers(headers: Iterable[tuple[bytes, bytes]]) -> dict[str, str]:
    return {name.decode("latin-1"): value.decode("latin-1") for name, value in headers}


async def _call_app(
    app: FastAPI,
    method: str,
    *,
    headers: Iterable[tuple[str, str]] | None = None,
) -> dict[str, object]:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": "/ping",
        "raw_path": b"/ping",
        "root_path": "",
        "query_string": b"",
        "headers": _encode_headers(headers or []),
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    response: dict[str, object] = {"status": None, "headers": [], "body": b""}
    body = b""
    received = False

    async def receive() -> dict[str, object]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return response


@pytest.mark.anyio()
async def test_allowed_origin_receives_cors_headers() -> None:
    origins = [TrustedCORSOrigin(origin="https://allowed.example", allow_credentials=False)]
    with configure_cors_app(origins) as app:
        preflight = await _call_app(
            app,
            "OPTIONS",
            headers=[
                ("origin", "https://allowed.example"),
                ("access-control-request-method", "GET"),
            ],
        )
        get_response = await _call_app(
            app,
            "GET",
            headers=[("origin", "https://allowed.example")],
        )

    preflight_headers = _decode_headers(preflight["headers"])
    get_headers = _decode_headers(get_response["headers"])

    assert preflight["status"] == 200
    assert preflight_headers["access-control-allow-origin"] == "https://allowed.example"
    assert "access-control-allow-credentials" not in preflight_headers
    assert get_response["status"] == 200
    assert get_headers["access-control-allow-origin"] == "https://allowed.example"
    assert "access-control-allow-credentials" not in get_headers


@pytest.mark.anyio()
async def test_disallowed_origin_gets_cors_error() -> None:
    origins = [TrustedCORSOrigin(origin="https://allowed.example", allow_credentials=False)]
    with configure_cors_app(origins) as app:
        response = await _call_app(
            app,
            "OPTIONS",
            headers=[
                ("origin", "https://malicious.example"),
                ("access-control-request-method", "GET"),
            ],
        )

    assert response["status"] == 400
    assert response["body"] in (b"Invalid CORS request", b"Disallowed CORS origin")


@pytest.mark.anyio()
async def test_credentials_allowed_only_when_requested() -> None:
    origins = [
        TrustedCORSOrigin(origin="https://public.example", allow_credentials=False),
        TrustedCORSOrigin(origin="https://secure.example", allow_credentials=True),
    ]
    with configure_cors_app(origins) as app:
        response = await _call_app(
            app,
            "OPTIONS",
            headers=[
                ("origin", "https://secure.example"),
                ("access-control-request-method", "GET"),
            ],
        )

    headers = _decode_headers(response["headers"])
    assert response["status"] == 200
    assert headers["access-control-allow-origin"] == "https://secure.example"
    assert headers["access-control-allow-credentials"] == "true"
