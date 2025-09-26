from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Sequence

import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("API_KEY", "test-secret")

import ai_invoice.service as invoice_service
from ai_invoice.config import settings
from ai_invoice.schemas import ClassificationResult
from api.license_validator import HEADER_NAME, LicenseClaims
from api.middleware import APIKeyAndLoggingMiddleware, BodyLimitMiddleware, configure_middleware
from api.routers import invoices as invoices_router
from api.routers.invoices import extract_invoice_endpoint
from api.security import reset_license_verifier_cache


pytestmark = pytest.mark.anyio()

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FEATURES = (
    "extract",
    "classify",
    "predict",
    "predictive",
    "predictive_train",
    "train",
)


def _generate_test_keypair(tmp_path: Path) -> tuple[Path, Path]:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"

    subprocess.run([
        "openssl",
        "genpkey",
        "-algorithm",
        "ed25519",
        "-out",
        str(private_path),
    ], check=True)
    subprocess.run([
        "openssl",
        "pkey",
        "-in",
        str(private_path),
        "-pubout",
        "-out",
        str(public_path),
    ], check=True)

    return private_path, public_path


def _normalize_timestamp(value: datetime | str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value


def _issue_token(
    private_key: Path,
    *,
    features: Sequence[str] | None = None,
    expires: datetime | str | None = None,
    issued_at: datetime | str | None = None,
    tenant_id: str = "tenant-123",
) -> str:
    expiration = expires or (datetime.now(timezone.utc) + timedelta(minutes=5))
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_license.py"),
        "--private-key",
        str(private_key),
        "--tenant-id",
        tenant_id,
        "--tenant-name",
        "Integration Tests",
        "--expires",
        _normalize_timestamp(expiration),
    ]

    feature_list = list(features or DEFAULT_FEATURES)
    for feature in feature_list:
        cmd.extend(["--feature", feature])

    if issued_at is not None:
        cmd.extend(["--issued-at", _normalize_timestamp(issued_at)])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    return payload["token"]


def _decode_artifact(token: str) -> dict[str, Any]:
    padding = "=" * ((4 - len(token) % 4) % 4)
    raw = base64.urlsafe_b64decode(token + padding)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("Decoded license artifact must be a mapping.")
    return data


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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
def license_guard(tmp_path: Path) -> Path:
    private_key, public_key = _generate_test_keypair(tmp_path)
    previous_path = settings.license_public_key_path
    previous_key = settings.license_public_key
    previous_revoked = settings.license_revoked_jtis
    previous_subjects = settings.license_revoked_subjects

    settings.license_public_key_path = str(public_key)
    settings.license_public_key = public_key.read_text(encoding="utf-8").strip() or None
    settings.license_revoked_jtis = frozenset()
    settings.license_revoked_subjects = frozenset()
    reset_license_verifier_cache()
    try:
        yield private_key
    finally:
        settings.license_public_key_path = previous_path
        settings.license_public_key = previous_key
        settings.license_revoked_jtis = previous_revoked
        settings.license_revoked_subjects = previous_subjects
        reset_license_verifier_cache()


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

    token = _issue_token(license_guard)
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
    previous_license_path = settings.license_public_key_path
    previous_license_key = settings.license_public_key
    settings.api_key = None
    settings.license_public_key_path = None
    settings.license_public_key = None
    try:
        middleware = _middleware()

        async def call_next(request: Request) -> Response:
            return Response("ok")

        request = _build_request(path="/health")
        response = await middleware.dispatch(request, call_next)
    finally:
        settings.api_key = previous_api_key
        settings.license_public_key_path = previous_license_path
        settings.license_public_key = previous_license_key

    assert response.status_code == 200


async def test_trial_fallback_allows_protected_request(
    api_key_guard, rate_limit_guard, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous_license_path = settings.license_public_key_path
    previous_license_key = settings.license_public_key
    trial_path = tmp_path / "trial.json"
    monkeypatch.setenv("AI_INVOICE_TRIAL_PATH", str(trial_path))
    settings.license_public_key_path = None
    settings.license_public_key = None

    middleware = _middleware()

    async def call_next(request: Request) -> Response:
        assert isinstance(request.state.license_claims, LicenseClaims)
        assert request.state.license_claims.has_feature("classify")
        return Response("ok")

    headers = [(b"x-api-key", b"test-secret")]
    request = _build_request(headers=headers)

    try:
        response = await middleware.dispatch(request, call_next)
    finally:
        settings.license_public_key_path = previous_license_path
        settings.license_public_key = previous_license_key
        monkeypatch.delenv("AI_INVOICE_TRIAL_PATH", raising=False)

    assert response.status_code == 200


async def test_trial_fallback_allows_router_access(
    api_key_guard, rate_limit_guard, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous_license_path = settings.license_public_key_path
    previous_license_key = settings.license_public_key

    trial_path = tmp_path / "trial-router.json"
    monkeypatch.setenv("AI_INVOICE_TRIAL_PATH", str(trial_path))
    settings.license_public_key_path = None
    settings.license_public_key = None

    app = FastAPI()
    configure_middleware(app)
    app.include_router(invoices_router.router)

    monkeypatch.setattr(
        invoice_service,
        "classify_text",
        lambda text: ClassificationResult(label="trial", proba=0.9),
    )

    headers = {"X-API-Key": settings.api_key or "test-secret"}

    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/invoices/classify",
                headers=headers,
                json={"text": "hola"},
            )
    finally:
        settings.license_public_key_path = previous_license_path
        settings.license_public_key = previous_license_key
        monkeypatch.delenv("AI_INVOICE_TRIAL_PATH", raising=False)

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"label": "trial", "proba": 0.9}


async def test_authorized_request_logs(
    api_key_guard, license_guard, rate_limit_guard, caplog: pytest.LogCaptureFixture
) -> None:

    async def call_next(request: Request) -> Response:
        assert isinstance(request.state.license_claims, LicenseClaims)
        assert request.state.license_claims.has_feature("classify")
        return Response("ok", media_type="application/json")

    middleware = _middleware()
    token = _issue_token(license_guard)
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

    issued_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    expires = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired_token = _issue_token(license_guard, issued_at=issued_at, expires=expires)
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

    async def call_next(request: Request) -> Response:  # pragma: no cover - unreachable
        return Response("ok")

    revoked_token = _issue_token(license_guard)
    artifact = _decode_artifact(revoked_token)
    token_id = artifact["payload"]["token_id"]
    settings.license_revoked_jtis = frozenset({token_id})
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
