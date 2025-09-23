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


def _get_csv_env(name: str) -> frozenset[str]:
    """Parse a comma-delimited environment variable into a frozen set."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return frozenset()
    entries = [segment.strip() for segment in raw.split(",") if segment.strip()]
    return frozenset(entries)


def _get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    truthy = {"1", "true", "t", "yes", "y", "on"}
    falsy = {"0", "false", "f", "no", "n", "off"}
    if value in truthy:
        return True
    if value in falsy:
        return False
    raise ValueError(
        "Environment variable %r must be a boolean value (one of %s or %s)."
        % (name, sorted(truthy), sorted(falsy))
    )


def _get_api_key() -> Optional[str]:
    """Support both AI_API_KEY (preferred) and API_KEY for backward compatibility."""
    key = os.getenv("AI_API_KEY") or os.getenv("API_KEY")
    if key is None:
        return None
    key = key.strip()
    return key or None


@dataclass(slots=True)
class Settings:
    # Model paths
    classifier_path: str = field(default_factory=lambda: os.getenv("CLASSIFIER_PATH", "models/classifier.joblib"))
    predictive_path: str = field(default_factory=lambda: os.getenv("PREDICTIVE_PATH", "models/predictive.joblib"))

    # Auth
    api_key: Optional[str] = field(default_factory=_get_api_key)
    # Explicit opt-out switch so devs must choose to run without an API key.
    allow_anonymous: bool = field(default_factory=lambda: _get_bool_env("ALLOW_ANONYMOUS", False))

    # Request validation
    max_upload_bytes: int = field(default_factory=lambda: _get_int_env("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    max_text_length: int = field(default_factory=lambda: _get_int_env("MAX_TEXT_LENGTH", 20_000))
    max_feature_fields: int = field(default_factory=lambda: _get_int_env("MAX_FEATURE_FIELDS", 50))
    max_json_body_bytes: Optional[int] = field(default_factory=lambda: _get_int_env("MAX_JSON_BODY_BYTES"))

    # Rate limiting knobs (not yet enforced in middleware)
    rate_limit_per_minute: Optional[int] = field(default_factory=lambda: _get_int_env("RATE_LIMIT_PER_MINUTE"))
    rate_limit_burst: Optional[int] = field(default_factory=lambda: _get_int_env("RATE_LIMIT_BURST"))

    # License verification (optional)
    license_public_key_path: Optional[str] = field(default_factory=lambda: os.getenv("LICENSE_PUBLIC_KEY_PATH"))
    license_public_key: Optional[str] = field(default_factory=lambda: os.getenv("LICENSE_PUBLIC_KEY"))
    license_algorithm: str = field(default_factory=lambda: os.getenv("LICENSE_ALGORITHM", "RS256"))
    license_revoked_jtis: frozenset[str] = field(default_factory=lambda: _get_csv_env("LICENSE_REVOKED_JTIS"))
    license_revoked_subjects: frozenset[str] = field(default_factory=lambda: _get_csv_env("LICENSE_REVOKED_SUBJECTS"))

    # CORS
    cors_trusted_origins: list[TrustedCORSOrigin] = field(default_factory=_get_cors_trusted_origins)

    def __post_init__(self) -> None:
        # Enforce explicit choice: either set an API key or opt into anonymous mode.
        if not self.api_key and not self.allow_anonymous:
            raise ValueError(
                "AI_API_KEY (or API_KEY) must be set unless ALLOW_ANONYMOUS=true is explicitly configured."
            )

        # Normalize/resolve license config
        if not self.license_public_key and self.license_public_key_path:
            try:
                with open(self.license_public_key_path, "r", encoding="utf-8") as handle:
                    object.__setattr__(self, "license_public_key", handle.read())
            except OSError as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    f"Unable to read license public key from {self.license_public_key_path!r}."
                ) from exc

        if self.license_public_key:
            object.__setattr__(self, "license_public_key", self.license_public_key.strip())

        alg = (self.license_algorithm or "RS256").strip().upper()
        object.__setattr__(self, "license_algorithm", alg or "RS256")

        # Ensure revoked sets are normalized (trim whitespace)
        cleaned_jtis = frozenset(entry.strip() for entry in self.license_revoked_jtis if entry.strip())
        cleaned_subjects = frozenset(entry.strip() for entry in self.license_revoked_subjects if entry.strip())
        object.__setattr__(self, "license_revoked_jtis", cleaned_jtis)
        object.__setattr__(self, "license_revoked_subjects", cleaned_subjects)


settings = Settings()
