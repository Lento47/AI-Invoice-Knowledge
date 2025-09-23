from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


def _get_int_env(name: str, default: Optional[int] = None) -> Optional[int]:
    """Read an integer environment variable with optional default."""

    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Environment variable {name!r} must be an integer.") from exc
    if value < 0:
        raise ValueError(f"Environment variable {name!r} must be non-negative.")
    return value


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


def _get_str_env(name: str) -> Optional[str]:
    """Read a string environment variable and normalize blanks to None."""

    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


@dataclass(slots=True)
class Settings:
    classifier_path: str = field(default_factory=lambda: os.getenv("CLASSIFIER_PATH", "models/classifier.joblib"))
    predictive_path: str = field(default_factory=lambda: os.getenv("PREDICTIVE_PATH", "models/predictive.joblib"))
    api_key: Optional[str] = field(default_factory=lambda: _get_str_env("API_KEY"))
    allow_anonymous: bool = field(default_factory=lambda: _get_bool_env("ALLOW_ANONYMOUS", False))
    max_upload_bytes: int = field(default_factory=lambda: _get_int_env("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    max_text_length: int = field(default_factory=lambda: _get_int_env("MAX_TEXT_LENGTH", 20_000))
    max_feature_fields: int = field(default_factory=lambda: _get_int_env("MAX_FEATURE_FIELDS", 50))
    max_json_body_bytes: Optional[int] = field(default_factory=lambda: _get_int_env("MAX_JSON_BODY_BYTES"))
    rate_limit_per_minute: Optional[int] = field(default_factory=lambda: _get_int_env("RATE_LIMIT_PER_MINUTE"))

    def __post_init__(self) -> None:
        if self.api_key is not None:
            normalized = self.api_key.strip()
            self.api_key = normalized or None

        if not self.api_key and not self.allow_anonymous:
            raise ValueError(
                "API_KEY environment variable must be set to a non-empty value unless "
                "ALLOW_ANONYMOUS is explicitly enabled."
            )


settings = Settings()
