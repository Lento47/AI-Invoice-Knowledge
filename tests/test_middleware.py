from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("API_KEY", "test-secret")

from ai_invoice.config import settings
from api.license_validator import HEADER_NAME, LicenseClaims
from api.middleware import APIKeyAndLoggingMiddleware, BodyLimitMiddleware
from api.routers.invoices import extract_invoice_endpoint


pytestmark = pytest.mark.anyio()

PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC2twz8UXSIGzHz
dEWJyPq3kCsDDovC+ohQ+mBO1ZCEAsmdWVn8QRdHQeNEnrdYA270YLgx+WivgayH
6Wje0WwuBzL818u2A6GQeBb60moUAXPJ80wNF+MT/0Bc3u2T5HS7Aa4OONrIh/QG
xLNq4S5c5a9KWYWiMizgSKcVvhhG9u9H3FSvBCgculS0Ktl9xOkhzPhKtoPHGs8f
tfiOKNl/6nH/nvKHJagKaNSIMNBctHx4KMzj8vplehkfAn7iC7inuG+9pqB+CWfm
VFafwkxnajxC+Y+THyhcFdsAw1js1JYdwn/Wcd9wDFSYItMzivy199bnuKqlbusN
/6LRZsGhAgMBAAECggEAFdzP0TYm6S1F3BFWy76QX1wBBYfdScqD+pqG4Q/1T5Js
0ObS2VfpguV7neeW3RFmGpgjGhmzgMKVpBqV6Ylp9hT28SGaFrCXCawQ5di9CCFH
W0wBFtT7nxYs+5/SEh7lJ8Yy7zE23oVD+fZZ2IlSrJtwDseo8Ygq7fhLg9K/4Wex
FfPKad6oj3+3pC5f1MmQJhmJU8hxkz05UWlz/Exl4bNbDCGyu24TEeV2wVUKVlMt
oaRIKLwKZA8HN0Ia1arHzdml+iMwMTMF5FIWSjZ+xyNSxdIn4OGdXXpyMLOn3lIQ
GJA8HTnuUh2yW5jXImKsMVZo9v29vdWHpDFYT3J+0QKBgQDxfSJaTxgZ+JLXhjQp
gWhmtVkF6qVDFoIkxSXRPwJknd/m9z3xAuPh4gIq4n/rDiQ/6WLb47SCY6Z4XNGS
Xsxj2uEyzIBMJ1yo5l7/SIpoSzqXcPJML8VeCLZlJj7S5ZDaBgbyboEW9BYuRHtY
IA6VXHdGEgtkeO4DO7x7lBkwmQKBgQDBscoFBz7jVE5M2+RCLSuVbSP90tENHq84
yGhDhfMwTJTB2GwkgCRHUl/NWAiLSmJe4/9x/fXgdlNlAee6oRT1PeDZhrot95ZC
IoXT6Dzk8kYXOQtg1VeDbq3YdI/REtkRQNS9rqZbfqmSXdVO0UEEvAxcheZyEmDI
bNcrS1jWSQKBgGPahUjoaaPbiAR8Zrc+3keR9xSeOOWrufawWnnSXw/xw/KCC2fL
9SSiypim/ZPZTh3rSEh6OFquD9i3MKUgc81aZUIXE3np0MO6Nk/C1BBaAwk518au
/iJq4dijXtjfueydD2RRUymFlmJdSM9gugcCrAMaVQGfi3Nk0QQcceoJAoGALeDR
q/06XRgj77qJx07xqtQOGVns4EGrWTTG1W+N2ZvaBEwh2Uds0GPngzjd1ThKMpWo
dLSln4QHXr5jx+XNlAUTFBMAWFDzizioIDg67DOifG+rjUUbFGuLy+BYDDp9pcOI
YGFU0AkhWyTUmHWiA+ASwXuJyO0ndXGqSXvwT9kCgYEAojbJNLGSo8rul3nVbx4L
NmfZYBBuAJeiDDh14wwtj9d+Z6viUwLpPkeS2uqs/S762h6WLdFOvCDgJPXeTs6y
B/jo0PV40IszgLjjo7DGO9Esamo68Na/kSWOFt10EQUB5fvPYF+8trtUzCB0pfXn
EvsUYXvDLEPJKdSMe3PMEpM=
-----END PRIVATE KEY-----"""

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtrcM/FF0iBsx83RFicj6
t5ArAw6LwvqIUPpgTtWQhALJnVlZ/EEXR0HjRJ63WANu9GC4Mflor4Gsh+lo3tFs
Lgcy/NfLtgOhkHgW+tJqFAFzyfNMDRfjE/9AXN7tk+R0uwGuDjjayIf0BsSzauEu
XOWvSlmFojIs4EinFb4YRvbvR9xUrwQoHLpUtCrZfcTpIcz4SraDxxrPH7X4jijZ
f+px/57yhyWoCmjUiDDQXLR8eCjM4/L6ZXoZHwJ+4gu4p7hvvaagfgln5lRWn8JM
Z2o8QvmPkx8oXBXbAMNY7NSWHcJ/1nHfcAxUmCLTM4r8tffW57iqpW7rDf+i0WbB
oQIDAQAB
-----END PUBLIC KEY-----"""

DEFAULT_FEATURES = (
    "extract",
    "classify",
    "predict",
    "predictive",
    "predictive_train",
    "train",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _openssl_sign(payload: bytes) -> bytes:
    with tempfile.NamedTemporaryFile("w", delete=False) as key_file:
        key_file.write(PRIVATE_KEY)
        key_path = key_file.name
    with tempfile.NamedTemporaryFile("wb", delete=False) as data_file:
        data_file.write(payload)
        data_path = data_file.name
    with tempfile.NamedTemporaryFile(delete=False) as sig_file:
        sig_path = sig_file.name
    try:
        subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path, "-out", sig_path, data_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        signature = Path(sig_path).read_bytes()
    finally:
        for path in (key_path, data_path, sig_path):
            try:
                os.unlink(path)
            except OSError:
                pass
    return signature


def _issue_token(**overrides: object) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "sub": overrides.pop("sub", "tenant-123"),
        "jti": overrides.pop("jti", "token-123"),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "features": overrides.pop("features", DEFAULT_FEATURES),
    }
    payload.update(overrides)
    header = {"alg": "RS256", "typ": "JWT"}
    header_segment = _b64url(json.dumps(header, separators=(',', ':'), sort_keys=True).encode("utf-8"))
    payload_segment = _b64url(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature_segment = _b64url(_openssl_sign(signing_input))
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _claims(*features: str) -> LicenseClaims:
    feature_list = list(features)
    return LicenseClaims(
        raw={
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
            "jti": "local-test",
            "features": feature_list,
        },
        features=frozenset(feature_list),
    )


def _build_request(
    headers: list[tuple[bytes, bytes]] | None = None, *, path: str = "/invoices/classify"
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
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
def license_guard() -> None:
    previous_key = settings.license_public_key
    previous_alg = settings.license_algorithm
    previous_revoked = settings.license_revoked_jtis
    previous_subjects = settings.license_revoked_subjects
    settings.license_public_key = PUBLIC_KEY
    settings.license_algorithm = "RS256"
    settings.license_revoked_jtis = frozenset()
    settings.license_revoked_subjects = frozenset()
    try:
        yield
    finally:
        settings.license_public_key = previous_key
        settings.license_algorithm = previous_alg
        settings.license_revoked_jtis = previous_revoked
        settings.license_revoked_subjects = previous_subjects


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
    api_key_guard, license_guard, rate_limit_guard, caplog: pytest.LogCaptureFixture
) -> None:
    middleware = _middleware()
    called = False

    async def call_next(request: Request) -> Response:
        nonlocal called
        called = True
        return Response("ok")

    token = _issue_token()
    request = _build_request(headers=[(HEADER_NAME.lower().encode(), token.encode())])
    with caplog.at_level(logging.INFO, logger="ai_invoice.api.middleware"):
        response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    assert not called
    record = caplog.records[-1]
    assert record.status_code == 401


async def test_missing_license_token_is_rejected(api_key_guard, license_guard) -> None:
    middleware = _middleware()

    async def call_next(request: Request) -> Response:  # pragma: no cover - unreachable
        return Response("ok")

    headers = [(b"x-api-key", b"test-secret")]
    request = _build_request(headers=headers)
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    assert response.body == b'{"detail":"Missing license token."}'


async def test_health_request_without_license_does_not_raise(rate_limit_guard) -> None:
    previous_api_key = settings.api_key
    previous_license_key = settings.license_public_key
    settings.api_key = None
    settings.license_public_key = None
    try:
        middleware = _middleware()

        async def call_next(request: Request) -> Response:
            return Response("ok")

        request = _build_request(path="/health")
        response = await middleware.dispatch(request, call_next)
    finally:
        settings.api_key = previous_api_key
        settings.license_public_key = previous_license_key

    assert response.status_code == 200


async def test_authorized_request_logs(
    api_key_guard, license_guard, rate_limit_guard, caplog: pytest.LogCaptureFixture
) -> None:

    async def call_next(request: Request) -> Response:
        assert isinstance(request.state.license_claims, LicenseClaims)
        assert request.state.license_claims.has_feature("classify")
        return Response("ok", media_type="application/json")

    middleware = _middleware()
    token = _issue_token()
    headers = [
        (b"x-api-key", b"test-secret"),
        (HEADER_NAME.lower().encode(), token.encode()),
    ]
    request = _build_request(headers=headers)

    with caplog.at_level(logging.INFO, logger="ai_invoice.api.middleware"):
        response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    log_records = [record for record in caplog.records if record.name == "ai_invoice.api.middleware"]
    assert log_records, "Expected middleware to emit a log entry"
    record = log_records[-1]
    assert record.status_code == 200
    assert record.method == "POST"
    assert record.path == "/invoices/classify"
    assert record.duration_ms >= 0
async def test_expired_license_token_rejected(api_key_guard, license_guard) -> None:
    middleware = _middleware()

    async def call_next(request: Request) -> Response:  # pragma: no cover - unreachable
        return Response("ok")

    expired_token = _issue_token(exp=int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()))
    headers = [
        (b"x-api-key", b"test-secret"),
        (HEADER_NAME.lower().encode(), expired_token.encode()),
    ]
    request = _build_request(headers=headers)
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 403
    assert response.body == b'{"detail":"License token expired."}'


async def test_revoked_license_token_rejected(api_key_guard, license_guard) -> None:
    middleware = _middleware()
    settings.license_revoked_jtis = frozenset({"revoked"})

    async def call_next(request: Request) -> Response:  # pragma: no cover - unreachable
        return Response("ok")

    revoked_token = _issue_token(jti="revoked")
    headers = [
        (b"x-api-key", b"test-secret"),
        (HEADER_NAME.lower().encode(), revoked_token.encode()),
    ]
    request = _build_request(headers=headers)
    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 403
    assert response.body == b'{"detail":"License token revoked."}'


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


@pytest.mark.anyio()
async def test_body_limit_allows_uploads_when_disabled() -> None:
    previous_limit = settings.max_upload_bytes
    settings.max_upload_bytes = 0
    try:
        async def asgi_app(scope, receive, send):  # pragma: no cover - dummy app
            return None

        middleware = BodyLimitMiddleware(asgi_app, max_len=settings.max_upload_bytes)

        async def call_next(request: Request) -> Response:
            return Response("ok")

        body = b"file-contents"
        request = _build_request(
            headers=[
                (b"content-length", str(len(body)).encode("latin-1")),
                (b"content-type", b"application/octet-stream"),
            ],
            path="/upload",
        )
        response = await middleware.dispatch(request, call_next)
    finally:
        settings.max_upload_bytes = previous_limit

    assert response.status_code == 200


@pytest.mark.anyio()
async def test_body_limit_allows_json_when_disabled() -> None:
    previous_limit = settings.max_upload_bytes
    settings.max_upload_bytes = 0
    try:
        async def asgi_app(scope, receive, send):  # pragma: no cover - dummy app
            return None

        middleware = BodyLimitMiddleware(asgi_app, max_len=settings.max_upload_bytes)

        async def call_next(request: Request) -> Response:
            return Response("ok", media_type="application/json")

        body = json.dumps({"message": "hello"}).encode("utf-8")
        request = _build_request(
            headers=[
                (b"content-length", str(len(body)).encode("latin-1")),
                (b"content-type", b"application/json"),
            ],
            path="/json",
        )
        response = await middleware.dispatch(request, call_next)
    finally:
        settings.max_upload_bytes = previous_limit

    assert response.status_code == 200


async def test_extract_invoice_large_file_rejected() -> None:
    previous_limit = settings.max_upload_bytes
    settings.max_upload_bytes = 5

    upload = UploadFile(filename="invoice.pdf", file=BytesIO(b"abcdef"))

    with pytest.raises(HTTPException) as exc:
        await extract_invoice_endpoint(file=upload, claims=_claims("extract"))

    settings.max_upload_bytes = previous_limit

    assert exc.value.status_code == 413
    assert "maximum size" in exc.value.detail
