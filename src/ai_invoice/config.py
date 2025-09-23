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


@dataclass(slots=True)
class Settings:
    classifier_path: str = field(default_factory=lambda: os.getenv("CLASSIFIER_PATH", "models/classifier.joblib"))
    predictive_path: str = field(default_factory=lambda: os.getenv("PREDICTIVE_PATH", "models/predictive.joblib"))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("API_KEY"))
    max_upload_bytes: int = field(default_factory=lambda: _get_int_env("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    max_text_length: int = field(default_factory=lambda: _get_int_env("MAX_TEXT_LENGTH", 20_000))
    max_feature_fields: int = field(default_factory=lambda: _get_int_env("MAX_FEATURE_FIELDS", 50))
    max_json_body_bytes: Optional[int] = field(default_factory=lambda: _get_int_env("MAX_JSON_BODY_BYTES"))
    rate_limit_per_minute: Optional[int] = field(default_factory=lambda: _get_int_env("RATE_LIMIT_PER_MINUTE"))


settings = Settings()
