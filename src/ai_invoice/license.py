"""Utilities for issuing and validating signed license artifacts."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


def _canonical_json(data: Mapping[str, Any]) -> bytes:
    """Serialize mappings to canonical JSON for signing/verification."""

    return json.dumps(data, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def canonicalize_payload(payload: Mapping[str, Any]) -> bytes:
    """Public helper exposed for signing workflows."""

    return _canonical_json(payload)


def _decode_datetime(value: Any) -> datetime:
    """Parse datetimes from ISO-8601 strings and coerce to UTC."""

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    else:  # pragma: no cover - defensive guard
        raise TypeError("datetime values must be ISO-8601 strings or datetime objects")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class LicenseVerificationError(Exception):
    """Raised when a license token cannot be validated."""


class LicenseExpiredError(LicenseVerificationError):
    """Raised when a license token has surpassed its expiration."""


class TenantInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LicensePayload(BaseModel):
    """Decoded license payload returned after verification."""

    model_config = ConfigDict(extra="forbid")

    tenant: TenantInfo
    features: list[str] = Field(default_factory=list)
    issued_at: datetime
    expires_at: datetime
    device: str | None = None
    token_id: str
    key_id: str | None = None

    @field_validator("issued_at", "expires_at", mode="before")
    @classmethod
    def _validate_dt(cls, value: Any) -> datetime:
        return _decode_datetime(value)


def encode_license_token(artifact: Mapping[str, Any]) -> str:
    """Produce a transport-safe token from a license artifact."""

    return base64.urlsafe_b64encode(_canonical_json(artifact)).decode("utf-8")


def decode_license_token(token: str) -> dict[str, Any]:
    """Inverse of :func:`encode_license_token` with validation hooks."""

    try:
        data = base64.urlsafe_b64decode(token.encode("utf-8"))
    except (ValueError, binascii.Error) as exc:  # pragma: no cover - sanity guard
        raise LicenseVerificationError("Token is not valid base64.") from exc
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:  # pragma: no cover - sanity guard
        raise LicenseVerificationError("Token did not decode to JSON.") from exc
    if not isinstance(parsed, dict):  # pragma: no cover - sanity guard
        raise LicenseVerificationError("Token must decode to an object.")
    return parsed


class LicenseVerifier:
    """Validate license tokens using a trusted Ed25519 public key."""

    def __init__(self, public_key_path: Path | None, *, public_key_data: str | None = None) -> None:
        if public_key_path is None and not public_key_data:
            raise ValueError("A public key path or PEM string must be provided.")

        self._public_key_path = Path(public_key_path) if public_key_path is not None else None
        self._public_key_data = public_key_data
        self._public_key: Ed25519PublicKey | None = None

    @classmethod
    def from_public_key_path(cls, path: str | Path) -> "LicenseVerifier":
        key_path = Path(path)
        if not key_path.exists():
            raise FileNotFoundError(f"Public key not found at {key_path}.")
        return cls(key_path)

    @classmethod
    def from_public_key_string(cls, data: str) -> "LicenseVerifier":
        normalized = data.strip()
        if not normalized:
            raise ValueError("Public key string must not be empty.")
        return cls(None, public_key_data=normalized)

    def _load_public_key(self) -> Ed25519PublicKey:
        if self._public_key is not None:
            return self._public_key

        if self._public_key_path is not None:
            try:
                key_bytes = self._public_key_path.read_bytes()
            except OSError as exc:  # pragma: no cover - defensive
                raise LicenseVerificationError("Public key file could not be read.") from exc
        else:
            if not self._public_key_data:  # pragma: no cover - defensive
                raise LicenseVerificationError("License verifier is missing public key data.")
            key_bytes = self._public_key_data.encode("utf-8")

        try:
            public_key = serialization.load_pem_public_key(key_bytes)
        except ValueError as exc:
            raise LicenseVerificationError("Public key is not valid PEM data.") from exc

        if not isinstance(public_key, Ed25519PublicKey):
            raise LicenseVerificationError("Public key must be an Ed25519 key.")

        self._public_key = public_key
        return public_key

    def _verify_signature(self, payload: bytes, signature: bytes) -> None:
        public_key = self._load_public_key()

        try:
            public_key.verify(signature, payload)
        except InvalidSignature as exc:
            raise LicenseVerificationError("License signature is invalid.") from exc

    def verify_token(self, token: str) -> LicensePayload:
        """Return the decoded payload if the token is authentic and unexpired."""

        artifact = decode_license_token(token)
        algorithm = artifact.get("algorithm")
        version = artifact.get("version")
        payload_obj = artifact.get("payload")
        signature_b64 = artifact.get("signature")

        if algorithm != "ed25519":
            raise LicenseVerificationError("Unsupported license algorithm.")
        if version != 1:
            raise LicenseVerificationError("Unsupported license version.")
        if not isinstance(payload_obj, Mapping) or not isinstance(signature_b64, str):
            raise LicenseVerificationError("Malformed license artifact.")

        try:
            signature = base64.urlsafe_b64decode(signature_b64.encode("utf-8"))
        except ValueError as exc:
            raise LicenseVerificationError("Signature is not base64 encoded.") from exc

        payload_bytes = _canonical_json(payload_obj)
        self._verify_signature(payload_bytes, signature)

        try:
            payload = LicensePayload.model_validate(payload_obj)
        except ValidationError as exc:
            raise LicenseVerificationError("License payload is malformed.") from exc

        now = datetime.now(timezone.utc)
        if payload.expires_at < now:
            raise LicenseExpiredError("License has expired.")

        return payload

