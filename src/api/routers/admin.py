from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from ai_invoice.config import (
    export_settings,
    get_environment_overrides,
    settings,
    update_persisted_settings,
)

from ..security import reset_license_verifier_cache


router = APIRouter(prefix="/admin", tags=["admin"])


class CorsOriginModel(BaseModel):
    origin: str = Field(..., min_length=1, description="CORS origin (e.g., https://app.example.com)")
    allow_credentials: bool = Field(
        False, description="Whether requests from this origin must include credentials"
    )

    @field_validator("origin")
    @classmethod
    def _normalize_origin(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("origin must not be empty")
        return normalized


class SettingsDocument(BaseModel):
    classifier_path: str
    predictive_path: str
    agent_model: str | None = Field(
        default=None,
        description="Model identifier used by LangGraph deep agents (e.g. openai:gpt-4o-mini)",
    )
    api_key: str | None = Field(default=None, description="API key required for client access")
    admin_api_key: str | None = Field(
        default=None, description="Secret used to access the administrative API"
    )
    allow_anonymous: bool = Field(
        False, description="Allow unauthenticated requests when no API key is present"
    )
    license_public_key_path: str | None = Field(default=None)
    license_public_key: str | None = Field(default=None)
    license_algorithm: str = Field("RS256", min_length=2)
    license_revoked_jtis: list[str] = Field(default_factory=list)
    license_revoked_subjects: list[str] = Field(default_factory=list)
    tls_certfile_path: str | None = Field(
        default=None,
        description="Path to a PEM certificate used for HTTPS termination when running uvicorn directly",
    )
    tls_keyfile_path: str | None = Field(
        default=None,
        description="Path to the private key that matches tls_certfile_path",
    )
    max_upload_bytes: int = Field(..., ge=0)
    max_text_length: int = Field(..., ge=0)
    max_feature_fields: int = Field(..., ge=0)
    max_json_body_bytes: int | None = Field(default=None, ge=0)
    rate_limit_per_minute: int | None = Field(default=None, ge=0)
    rate_limit_burst: int | None = Field(default=None, ge=0)
    cors_trusted_origins: list[CorsOriginModel] = Field(default_factory=list)

    @field_validator("license_algorithm")
    @classmethod
    def _normalize_algorithm(cls, value: str) -> str:
        normalized = value.strip().upper()
        return normalized or "RS256"

    @field_validator("license_revoked_jtis", "license_revoked_subjects", mode="before")
    @classmethod
    def _clean_revoked(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (set, frozenset, tuple)):
            iterable = list(value)
        elif isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        else:
            iterable = value
        return [str(item).strip() for item in iterable if str(item).strip()]


class SettingsEnvelope(BaseModel):
    values: SettingsDocument
    overrides: dict[str, bool]


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    secret = getattr(settings, "admin_api_key", None)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrative API is not configured.",
        )
    if not x_admin_token or not hmac.compare_digest(secret, x_admin_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token.")


@router.get("/settings", response_model=SettingsEnvelope)
def read_settings(_: None = Depends(require_admin_token)) -> SettingsEnvelope:
    payload = export_settings()
    document = SettingsDocument(**payload)
    overrides = get_environment_overrides()
    return SettingsEnvelope(values=document, overrides=overrides)


@router.put("/settings", response_model=SettingsEnvelope)
def update_settings(document: SettingsDocument, _: None = Depends(require_admin_token)) -> SettingsEnvelope:
    payload = document.model_dump()
    payload["cors_trusted_origins"] = [
        {
            "origin": item.origin,
            "allow_credentials": item.allow_credentials,
        }
        for item in document.cors_trusted_origins
    ]
    update_persisted_settings(payload)
    reset_license_verifier_cache()
    refreshed = export_settings()
    overrides = get_environment_overrides()
    return SettingsEnvelope(values=SettingsDocument(**refreshed), overrides=overrides)


__all__ = ["router"]

