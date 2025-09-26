from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from fastapi import HTTPException, Request, status

from ai_invoice.config import Settings, settings
from ai_invoice.license import LicensePayload


HEADER_NAME = "X-License"


@dataclass(frozen=True, slots=True)
class LicenseClaims:
    """Validated license claims attached to incoming requests."""

    raw: Mapping[str, Any]
    features: frozenset[str]
    payload: LicensePayload | None = None

    def __getitem__(self, item: str) -> Any:
        return self.raw[item]

    def get(self, item: str, default: Any | None = None) -> Any:
        return self.raw.get(item, default)

    @property
    def expires_at(self) -> datetime | None:
        if self.payload is not None:
            return self.payload.expires_at

        exp = self.raw.get("expires_at") or self.raw.get("exp")
        if isinstance(exp, datetime):
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return exp.astimezone(timezone.utc)
        if isinstance(exp, str):
            try:
                normalized = exp.replace("Z", "+00:00")
                dt = datetime.fromisoformat(normalized)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        if isinstance(exp, (int, float)):
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None

    def has_feature(self, feature: str) -> bool:
        return feature in self.features


def _normalize_features(values: Sequence[str]) -> frozenset[str]:
    normalized = [item.strip() for item in values if isinstance(item, str) and item.strip()]
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License payload is missing feature permissions.",
        )
    return frozenset(normalized)


def build_license_claims(
    payload: LicensePayload, *, config: Settings | None = None
) -> LicenseClaims:
    """Normalize a verified payload into the API's claim structure."""

    cfg = config or settings

    features = _normalize_features(payload.features)

    revoked_ids = getattr(cfg, "license_revoked_jtis", frozenset())
    if payload.token_id in revoked_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token revoked.")

    revoked_subjects = getattr(cfg, "license_revoked_subjects", frozenset())
    tenant_id = payload.tenant.id
    if tenant_id in revoked_subjects:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token revoked.")

    raw = payload.model_dump(mode="json")
    return LicenseClaims(raw=raw, features=features, payload=payload)


def ensure_feature(claims: LicenseClaims | None, feature: str) -> LicenseClaims:
    """Ensure the provided claims include a specific feature permission."""

    normalized = feature.strip()
    if not normalized:
        raise ValueError("Feature name must be a non-empty string.")
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing license token.")
    if normalized not in claims.features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"License does not permit '{normalized}' operations.",
        )
    return claims


def get_license_claims(request: Request) -> LicenseClaims:
    trial_error = getattr(request.state, "trial_error_detail", None)
    if isinstance(trial_error, str) and trial_error.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=trial_error)
    claims = getattr(request.state, "license_claims", None)
    if not isinstance(claims, LicenseClaims):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing license token.")
    return claims


def require_feature_flag(feature: str) -> Callable[[Request], LicenseClaims]:
    """FastAPI dependency that enforces the presence of a license feature."""

    def _dependency(request: Request) -> LicenseClaims:
        claims = get_license_claims(request)
        return ensure_feature(claims, feature)

    return _dependency
