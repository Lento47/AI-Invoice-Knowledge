from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class TrustedCORSOrigin:
    """Trusted origin entry describing credential requirements."""
    origin: str
    allow_credentials: bool = False


def _parse_bool_env(value: str) -> bool:
    """Parse common boolean environment values."""
    normalized = value.strip().lower()
    truthy = {"1", "true", "t", "yes", "y", "on", "credentials"}
    falsy = {"0", "false", "f", "no", "n", "off"}
    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    raise ValueError(
        "Environment variable CORS_TRUSTED_ORIGINS contains an invalid boolean value: "
        f"{value!r}."
    )


def _get_cors_trusted_origins() -> list[TrustedCORSOrigin]:
    """Read trusted CORS origins from the environment.

    Format (comma-separated):
      - "*"
      - "https://example.com"
      - "https://app.example.com|true"  # allow credentials for this origin

    Rules:
      - Wildcard '*' cannot be combined with other origins.
      - Credentials cannot be required for wildcard origins.
    """
    raw = os.getenv("CORS_TRUSTED_ORIGINS")
    if raw is None or raw.strip() == "":
        return [TrustedCORSOrigin(origin="*", allow_credentials=False)]

    entries: list[TrustedCORSOrigin] = []
    for chunk in raw.split(","):
        entry = chunk.strip()
        if not entry:
            continue

        allow_credentials = False
        if "|" in entry:
            origin_part, flag_part = entry.split("|", 1)
            origin = origin_part.strip()
            if not origin:
                raise ValueError(
                    "CORS_TRUSTED_ORIGINS entries must include an origin before the credential flag."
                )
            allow_credentials = _parse_bool_env(flag_part)
        else:
            origin = entry

        if origin == "*":
            if allow_credentials:
                raise ValueError(
                    "CORS_TRUSTED_ORIGINS may not require credentials for wildcard origins."
                )
            if entries:
                raise ValueError(
                    "CORS_TRUSTED_ORIGINS wildcard origin cannot be combined with other origins."
                )

        if any(existing.origin == "*" for existing in entries):
            raise ValueError(
                "CORS_TRUSTED_ORIGINS wildcard origin cannot be combined with other origins."
            )

        entries.append(TrustedCORSOrigin(origin=origin, allow_credentials=allow_credentials))

    return entries or [TrustedCORSOrigin(origin="*", allow_credentials=False)]


def _get_int_env(name: str, default: Optional[int] = None) -> Optional[int]:
    """Read an integer environment variable with optional default."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Environment variable {name!r} must be an integer.") from exc
    if value < 0:
        raise ValueError(f"Environment variable {name!r} must be non-negative.")
    return value


def _get_api_key() -> Optional[str]:
    """Support both AI_API_KEY (preferred) and API_KEY for backward compatibility."""
    return os.getenv("AI_API_KEY") or os.getenv("API_KEY")


@dataclass(slots=True)
class Settings:
    classifier_path: str = field(default_factory=lambda: os.getenv("CLASSIFIER_PATH", "models/classifier.joblib"))
    predictive_path: str = field(default_factory=lambda: os.getenv("PREDICTIVE_PATH", "models/predictive.joblib"))

    # Auth
    api_key: Optional[str] = field(default_factory=_get_api_key)

    # Request validation
    max_upload_bytes: int = field(default_factory=lambda: _get_int_env("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    max_text_length: int = field(default_factory=lambda: _get_int_env("MAX_TEXT_LENGTH", 20_000))
    max_feature_fields: int = field(default_factory=lambda: _get_int_env("MAX_FEATURE_FIELDS", 50))
    max_json_body_bytes: Optional[int] = field(default_factory=lambda: _get_int_env("MAX_JSON_BODY_BYTES"))

    # Rate limiting knobs (not yet enforced in middleware)
    rate_limit_per_minute: Optional[int] = field(default_factory=lambda: _get_int_env("RATE_LIMIT_PER_MINUTE"))
    rate_limit_burst: Optional[int] = field(default_factory=lambda: _get_int_env("RATE_LIMIT_BURST"))

    # CORS
    cors_trusted_origins: list[TrustedCORSOrigin] = field(default_factory=_get_cors_trusted_origins)


settings = Settings()
