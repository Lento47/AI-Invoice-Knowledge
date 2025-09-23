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


@lru_cache(maxsize=4)
def _build_verifier(public_key_path: str) -> LicenseVerifier:
    return LicenseVerifier.from_public_key_path(public_key_path)


def reset_license_verifier_cache() -> None:
    """Clear cached verifier instances (useful for tests and key rotation)."""

    _build_verifier.cache_clear()  # type: ignore[attr-defined]


def get_license_verifier() -> LicenseVerifier:
    public_key_path = getattr(settings, "license_public_key_path", None)
    if not public_key_path:
        raise RuntimeError("LICENSE_PUBLIC_KEY_PATH is not configured.")
    return _build_verifier(public_key_path)


def require_license_token(request: Request) -> LicensePayload:
    token = request.headers.get("X-License")
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

