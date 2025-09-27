"""Helpers for creating signed license artifacts."""

from __future__ import annotations

import base64
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .license import canonicalize_payload, encode_license_token


def isoformat_utc(dt: datetime) -> str:
    """Return an ISO-8601 timestamp in UTC with trailing ``Z``."""
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sign_payload(private_key: Path, payload: bytes, password_file: Path | None = None) -> bytes:
    """Sign ``payload`` with the Ed25519 private key using OpenSSL."""
    with tempfile.NamedTemporaryFile(delete=False) as payload_file:
        payload_file.write(payload)
        payload_path = Path(payload_file.name)

    signature_path = Path(tempfile.NamedTemporaryFile(delete=False).name)

    cmd = [
        "openssl",
        "pkeyutl",
        "-sign",
        "-inkey",
        str(private_key),
        "-rawin",
        "-in",
        str(payload_path),
        "-out",
        str(signature_path),
    ]
    if password_file is not None:
        cmd.extend(["-passin", f"file:{password_file}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        payload_path.unlink(missing_ok=True)
        signature_path.unlink(missing_ok=True)
        raise RuntimeError("OpenSSL executable is required to sign licenses.") from exc

    payload_path.unlink(missing_ok=True)
    if result.returncode != 0:
        signature_path.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "").strip()
        message = (
            f"License signing failed via OpenSSL ({detail})."
            if detail
            else "License signing failed via OpenSSL."
        )
        raise RuntimeError(message)

    signature = signature_path.read_bytes()
    signature_path.unlink(missing_ok=True)
    return signature


def generate_license_artifact(
    *,
    private_key: Path,
    password_file: Path | None,
    tenant: dict[str, Any],
    features: list[str] | None,
    issued_at: datetime,
    expires_at: datetime,
    device: str | None = None,
    key_id: str | None = None,
    token_id: str | None = None,
    certificate: dict[str, Any] | None = None,
    algorithm: str = "ed25519",
) -> tuple[dict[str, Any], str]:
    """Build and sign a license artifact, returning the artifact and encoded token.

    ``certificate`` can include human-readable metadata (for example, a contract
    or business name) that is embedded alongside the canonical payload.
    """
    payload: dict[str, Any] = {
        "tenant": tenant,
        "features": features or [],
        "issued_at": isoformat_utc(issued_at),
        "expires_at": isoformat_utc(expires_at),
        "token_id": token_id or str(uuid.uuid4()),
    }
    if device:
        payload["device"] = device
    if key_id:
        payload["key_id"] = key_id
    if certificate:
        payload["certificate"] = certificate

    payload_bytes = canonicalize_payload(payload)
    signature = sign_payload(private_key, payload_bytes, password_file)

    artifact = {
        "version": 1,
        "algorithm": algorithm,
        "payload": payload,
        "signature": base64.urlsafe_b64encode(signature).decode("utf-8"),
    }
    token = encode_license_token(artifact)
    return artifact, token
