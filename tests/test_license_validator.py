from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import HTTPException
from starlette.requests import Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("API_KEY", "test-secret")

from ai_invoice.config import settings
from api.license_validator import HEADER_NAME, get_license_claims
from api.security import reset_license_verifier_cache, require_license_token


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


def _run_cli(private_key: Path, **kwargs: str) -> dict[str, object]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_license.py"),
        "--private-key",
        str(private_key),
        "--tenant-id",
        "tenant-123",
        "--tenant-name",
        "Acme Co",
        "--feature",
        "ocr",
        "--feature",
        "classification",
    ]

    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", value])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


@pytest.fixture()
def configure_license(tmp_path: Path) -> Iterator[tuple[Path, Path]]:
    private_key, public_key = _generate_test_keypair(tmp_path)
    previous = settings.license_public_key_path
    settings.license_public_key_path = str(public_key)
    reset_license_verifier_cache()
    try:
        yield private_key, public_key
    finally:
        settings.license_public_key_path = previous
        reset_license_verifier_cache()


def _build_request(token: str | None, *, header_name: str = HEADER_NAME) -> Request:
    headers = []
    if token is not None:
        headers.append((header_name.lower().encode("utf-8"), token.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/protected",
        "headers": headers,
        "scheme": "http",
    }
    return Request(scope)


def test_validator_accepts_cli_token(configure_license: tuple[Path, Path]) -> None:
    private_key, _ = configure_license
    expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    response = _run_cli(private_key, expires=expires)
    token = response["token"]

    request = _build_request(token)
    payload = require_license_token(request)

    assert payload.tenant.id == "tenant-123"
    assert request.state.license_payload is payload


def test_validator_rejects_tampered_and_expired_tokens(configure_license: tuple[Path, Path]) -> None:
    private_key, _ = configure_license
    expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = _run_cli(private_key, expires=expires)
    token = response["token"]

    raw = base64.urlsafe_b64decode(token.encode("utf-8"))
    artifact = json.loads(raw)
    artifact["payload"]["tenant"]["id"] = "tampered"
    tampered_token = base64.urlsafe_b64encode(
        json.dumps(artifact, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8")

    request = _build_request(tampered_token)
    with pytest.raises(HTTPException) as invalid_exc:
        require_license_token(request)
    assert invalid_exc.value.status_code == 401
    assert "invalid" in invalid_exc.value.detail.lower()

    expired = _run_cli(
        private_key,
        issued_at="2023-01-01T00:00:00Z",
        expires="2023-02-01T00:00:00Z",
    )
    expired_token = expired["token"]

    expired_request = _build_request(expired_token)

    with pytest.raises(HTTPException) as expired_exc:
        require_license_token(expired_request)
    assert expired_exc.value.status_code == 401
    assert "expired" in expired_exc.value.detail.lower()


def test_portal_headers_allow_license_access(configure_license: tuple[Path, Path]) -> None:
    private_key, _ = configure_license
    expires = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    response = _run_cli(private_key, expires=expires)
    token = response["token"]

    request = _build_request(token, header_name=HEADER_NAME)
    request.scope["headers"].append((b"x-api-key", b"test-secret"))

    payload = require_license_token(request)

    assert payload.tenant.id == "tenant-123"
    assert request.headers.get(HEADER_NAME) == token


def test_get_license_claims_raises_when_trial_expired() -> None:
    request = _build_request(token=None)
    request.state.trial_error_detail = "Trial expired"

    with pytest.raises(HTTPException) as exc:
        get_license_claims(request)

    assert exc.value.status_code == 403
    assert "expired" in exc.value.detail.lower()


def test_inline_public_key_configuration(tmp_path: Path) -> None:
    private_key, public_key_path = _generate_test_keypair(tmp_path)
    public_key_data = public_key_path.read_text(encoding="utf-8")

    previous_path = settings.license_public_key_path
    previous_data = settings.license_public_key
    settings.license_public_key_path = None
    settings.license_public_key = public_key_data
    reset_license_verifier_cache()

    try:
        expires = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        response = _run_cli(private_key, expires=expires)
        token = response["token"]

        request = _build_request(token)
        payload = require_license_token(request)

        assert payload.tenant.id == "tenant-123"
        assert request.state.license_payload is payload
    finally:
        settings.license_public_key_path = previous_path
        settings.license_public_key = previous_data
        reset_license_verifier_cache()

