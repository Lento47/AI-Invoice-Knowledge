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


def _get_csv_env(name: str) -> frozenset[str]:
    """Parse a comma-delimited environment variable into a frozen set."""

    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return frozenset()
    entries = [segment.strip() for segment in raw.split(",") if segment.strip()]
    return frozenset(entries)


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
    license_public_key_path: Optional[str] = field(
        default_factory=lambda: os.getenv("LICENSE_PUBLIC_KEY_PATH")
    )
    license_public_key: Optional[str] = field(default_factory=lambda: os.getenv("LICENSE_PUBLIC_KEY"))
    license_algorithm: str = field(default_factory=lambda: os.getenv("LICENSE_ALGORITHM", "RS256"))
    license_revoked_jtis: frozenset[str] = field(
        default_factory=lambda: _get_csv_env("LICENSE_REVOKED_JTIS")
    )
    license_revoked_subjects: frozenset[str] = field(
        default_factory=lambda: _get_csv_env("LICENSE_REVOKED_SUBJECTS")
    )

    def __post_init__(self) -> None:
        if not self.license_public_key and self.license_public_key_path:
            try:
                with open(self.license_public_key_path, "r", encoding="utf-8") as handle:
                    self.license_public_key = handle.read()
            except OSError as exc:  # pragma: no cover - defensive branch
                raise RuntimeError(
                    f"Unable to read license public key from {self.license_public_key_path!r}."
                ) from exc
        if self.license_public_key:
            self.license_public_key = self.license_public_key.strip()
        alg = (self.license_algorithm or "RS256").strip()
        self.license_algorithm = alg.upper() if alg else "RS256"
        self.license_revoked_jtis = frozenset(
            entry.strip() for entry in self.license_revoked_jtis if entry.strip()
        )
        self.license_revoked_subjects = frozenset(
            entry.strip() for entry in self.license_revoked_subjects if entry.strip()
        )


settings = Settings()
