"""Security helpers for validating deployment licenses."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, Request, status

from ai_invoice.config import settings
from ai_invoice.license import (
    LicenseExpiredError,
    LicensePayload,
    LicenseVerificationError,
    LicenseVerifier,
)

from .license_validator import HEADER_NAME


@lru_cache(maxsize=4)
def _build_verifier(public_key_path: str | None, public_key_data: str | None) -> LicenseVerifier:
    if public_key_data:
        return LicenseVerifier.from_public_key_string(public_key_data)
    if public_key_path:
        return LicenseVerifier.from_public_key_path(public_key_path)
    raise RuntimeError("License public key configuration is missing.")


def reset_license_verifier_cache() -> None:
    """Clear cached verifier instances (useful for tests and key rotation)."""

    _build_verifier.cache_clear()  # type: ignore[attr-defined]


def get_license_verifier() -> LicenseVerifier:
    public_key_path = getattr(settings, "license_public_key_path", None)
    if public_key_path:
        return _build_verifier(public_key_path, None)

    public_key_data = getattr(settings, "license_public_key", None)
    if public_key_data:
        return _build_verifier(None, public_key_data)

    raise RuntimeError("LICENSE_PUBLIC_KEY_PATH or LICENSE_PUBLIC_KEY must be configured.")


def require_license_token(request: Request) -> LicensePayload:
    token = request.headers.get(HEADER_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="License token is required.")

    try:
        verifier = get_license_verifier()
    except Exception as exc:  # pragma: no cover - defensive branch
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="License verification unavailable.",
        ) from exc

    try:
        payload = verifier.verify_token(token.strip())
    except LicenseExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="License token has expired.") from exc
    except LicenseVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="License token is invalid.") from exc

    request.state.license_payload = payload
    return payload

