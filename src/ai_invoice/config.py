"""Application configuration and persistence helpers."""

from __future__ import annotations

import copy
import os
from dataclasses import MISSING, dataclass, field, fields
from typing import Any, Optional

from .settings_store import SettingsStore


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


def _default_cors_origins() -> list[TrustedCORSOrigin]:
    return [TrustedCORSOrigin(origin="*", allow_credentials=False)]


def _get_cors_trusted_origins() -> list[TrustedCORSOrigin]:
    """Read trusted CORS origins from the environment."""

    raw = os.getenv("CORS_TRUSTED_ORIGINS")
    if raw is None or raw.strip() == "":
        return _default_cors_origins()

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

    return entries or _default_cors_origins()


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


def _normalize_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def _coerce_required_int(value: Any, field_name: str) -> int:
    coerced = _coerce_optional_int(value, field_name)
    if coerced is None:
        raise ValueError(f"{field_name} must be configured with a non-negative integer.")
    return coerced


def _coerce_optional_int(value: Any, field_name: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer, not a boolean.")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{field_name} must be non-negative.")
        return value
    text = str(value).strip()
    if text == "":
        return None
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer value.") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return parsed


def _normalize_str_collection(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (set, frozenset, list, tuple)):
        items = value
    else:
        items = [value]
    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


@dataclass(slots=True)
class Settings:
    """Application configuration sourced from persisted storage and environment."""

    # Model paths
    classifier_path: str = "models/classifier.joblib"
    predictive_path: str = "models/predictive.joblib"
    agent_model: Optional[str] = None

    # Auth
    api_key: Optional[str] = None
    admin_api_key: Optional[str] = None
    allow_anonymous: bool = False

    # License configuration
    license_public_key_path: Optional[str] = None
    license_public_key: Optional[str] = None
    license_algorithm: str = "RS256"
    license_revoked_jtis: frozenset[str] = field(default_factory=frozenset)
    license_revoked_subjects: frozenset[str] = field(default_factory=frozenset)

    # Transport security
    tls_certfile_path: Optional[str] = None
    tls_keyfile_path: Optional[str] = None

    # Request validation
    max_upload_bytes: int = 5 * 1024 * 1024
    max_text_length: int = 20_000
    max_feature_fields: int = 50
    max_json_body_bytes: Optional[int] = None

    # Rate limiting knobs (not yet enforced in middleware)
    rate_limit_per_minute: Optional[int] = None
    rate_limit_burst: Optional[int] = None

    # CORS
    cors_trusted_origins: list[TrustedCORSOrigin] = field(default_factory=_default_cors_origins)

    def __post_init__(self) -> None:
        self.classifier_path = self.classifier_path.strip()
        self.predictive_path = self.predictive_path.strip()

        self.api_key = _normalize_optional_str(self.api_key)
        self.admin_api_key = _normalize_optional_str(self.admin_api_key)
        self.agent_model = _normalize_optional_str(self.agent_model)
        self.allow_anonymous = bool(self.allow_anonymous)

        self.license_public_key_path = _normalize_optional_str(self.license_public_key_path)
        self.license_public_key = _normalize_optional_str(self.license_public_key)

        self.tls_certfile_path = _normalize_optional_str(self.tls_certfile_path)
        self.tls_keyfile_path = _normalize_optional_str(self.tls_keyfile_path)

        if bool(self.tls_certfile_path) ^ bool(self.tls_keyfile_path):
            raise ValueError(
                "TLS configuration requires both tls_certfile_path and tls_keyfile_path or neither."
            )

        self.license_revoked_jtis = frozenset(_normalize_str_collection(self.license_revoked_jtis))
        self.license_revoked_subjects = frozenset(
            _normalize_str_collection(self.license_revoked_subjects)
        )

        self.max_upload_bytes = _coerce_required_int(self.max_upload_bytes, "max_upload_bytes")
        self.max_text_length = _coerce_required_int(self.max_text_length, "max_text_length")
        self.max_feature_fields = _coerce_required_int(
            self.max_feature_fields, "max_feature_fields"
        )
        self.max_json_body_bytes = _coerce_optional_int(
            self.max_json_body_bytes, "max_json_body_bytes"
        )
        self.rate_limit_per_minute = _coerce_optional_int(
            self.rate_limit_per_minute, "rate_limit_per_minute"
        )
        self.rate_limit_burst = _coerce_optional_int(self.rate_limit_burst, "rate_limit_burst")

        if not self.api_key and not self.allow_anonymous:
            raise ValueError(
                "AI_API_KEY (or API_KEY) must be set unless ALLOW_ANONYMOUS=true is explicitly configured."
            )

        if not self.admin_api_key and self.api_key:
            self.admin_api_key = self.api_key

        if self.license_public_key_path and not self.license_public_key:
            try:
                with open(self.license_public_key_path, "r", encoding="utf-8") as handle:
                    self.license_public_key = handle.read().strip() or None
            except OSError as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    f"Unable to read license public key from {self.license_public_key_path!r}."
                ) from exc

        if self.license_public_key:
            self.license_public_key = self.license_public_key.strip()

        alg = (self.license_algorithm or "RS256").strip().upper()
        self.license_algorithm = alg or "RS256"

        self.cors_trusted_origins = self._normalize_cors_entries(self.cors_trusted_origins)

    @staticmethod
    def _normalize_cors_entries(
        raw_entries: list[TrustedCORSOrigin] | list[dict[str, Any]] | list[Any]
    ) -> list[TrustedCORSOrigin]:
        entries: list[TrustedCORSOrigin] = []
        for entry in raw_entries or []:
            if isinstance(entry, TrustedCORSOrigin):
                entries.append(entry)
                continue
            if isinstance(entry, dict):
                origin = _normalize_optional_str(entry.get("origin"))
                if not origin:
                    raise ValueError("CORS origins must include a non-empty origin value.")
                allow_credentials = bool(entry.get("allow_credentials", False))
                entries.append(TrustedCORSOrigin(origin=origin, allow_credentials=allow_credentials))
                continue
            if isinstance(entry, str):
                origin = entry.strip()
                if origin:
                    entries.append(TrustedCORSOrigin(origin=origin, allow_credentials=False))
                continue
            raise TypeError(
                "cors_trusted_origins entries must be dicts, strings, or TrustedCORSOrigin instances."
            )

        if not entries:
            entries = _default_cors_origins()

        wildcard = [item for item in entries if item.origin == "*"]
        if wildcard:
            if len(entries) > len(wildcard):
                raise ValueError("CORS wildcard origin cannot be combined with other origins.")
            if any(item.allow_credentials for item in wildcard):
                raise ValueError("CORS wildcard origin may not require credentials.")

        return entries


_settings_store = SettingsStore()
_SETTINGS_FIELD_NAMES = {field.name for field in fields(Settings)}
_ENV_OVERRIDE_FIELDS: set[str] = set()


def _settings_defaults() -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for item in fields(Settings):
        if item.default is not MISSING:
            defaults[item.name] = copy.deepcopy(item.default)
        elif item.default_factory is not MISSING:  # type: ignore[attr-defined]
            defaults[item.name] = item.default_factory()
    return defaults


def _sanitize_store_data(raw: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in raw.items():
        if key in _SETTINGS_FIELD_NAMES:
            sanitized[key] = copy.deepcopy(value)
    return sanitized


def _collect_env_overrides(base: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    overrides: dict[str, Any] = {}
    override_fields: set[str] = set()

    if "CLASSIFIER_PATH" in os.environ:
        overrides["classifier_path"] = os.getenv("CLASSIFIER_PATH") or base.get("classifier_path")
        override_fields.add("classifier_path")

    if "PREDICTIVE_PATH" in os.environ:
        overrides["predictive_path"] = os.getenv("PREDICTIVE_PATH") or base.get("predictive_path")
        override_fields.add("predictive_path")

    if "AGENT_MODEL" in os.environ:
        overrides["agent_model"] = _normalize_optional_str(os.getenv("AGENT_MODEL"))
        override_fields.add("agent_model")

    if any(env in os.environ for env in ("AI_API_KEY", "API_KEY")):
        overrides["api_key"] = _get_api_key()
        override_fields.add("api_key")

    if "ADMIN_API_KEY" in os.environ:
        overrides["admin_api_key"] = _normalize_optional_str(os.getenv("ADMIN_API_KEY"))
        override_fields.add("admin_api_key")

    if "ALLOW_ANONYMOUS" in os.environ:
        overrides["allow_anonymous"] = _get_bool_env(
            "ALLOW_ANONYMOUS", bool(base.get("allow_anonymous", False))
        )
        override_fields.add("allow_anonymous")

    if "LICENSE_PUBLIC_KEY_PATH" in os.environ:
        overrides["license_public_key_path"] = _normalize_optional_str(
            os.getenv("LICENSE_PUBLIC_KEY_PATH")
        )
        override_fields.add("license_public_key_path")

    if "LICENSE_PUBLIC_KEY" in os.environ:
        overrides["license_public_key"] = _normalize_optional_str(
            os.getenv("LICENSE_PUBLIC_KEY")
        )
        override_fields.add("license_public_key")

    if "TLS_CERTFILE_PATH" in os.environ:
        overrides["tls_certfile_path"] = _normalize_optional_str(
            os.getenv("TLS_CERTFILE_PATH")
        )
        override_fields.add("tls_certfile_path")

    if "TLS_KEYFILE_PATH" in os.environ:
        overrides["tls_keyfile_path"] = _normalize_optional_str(
            os.getenv("TLS_KEYFILE_PATH")
        )
        override_fields.add("tls_keyfile_path")

    if "LICENSE_ALGORITHM" in os.environ:
        overrides["license_algorithm"] = os.getenv("LICENSE_ALGORITHM")
        override_fields.add("license_algorithm")

    if "LICENSE_REVOKED_JTIS" in os.environ:
        overrides["license_revoked_jtis"] = _get_csv_env("LICENSE_REVOKED_JTIS")
        override_fields.add("license_revoked_jtis")

    if "LICENSE_REVOKED_SUBJECTS" in os.environ:
        overrides["license_revoked_subjects"] = _get_csv_env("LICENSE_REVOKED_SUBJECTS")
        override_fields.add("license_revoked_subjects")

    if "MAX_UPLOAD_BYTES" in os.environ:
        overrides["max_upload_bytes"] = _get_int_env(
            "MAX_UPLOAD_BYTES", base.get("max_upload_bytes")
        )
        override_fields.add("max_upload_bytes")

    if "MAX_TEXT_LENGTH" in os.environ:
        overrides["max_text_length"] = _get_int_env(
            "MAX_TEXT_LENGTH", base.get("max_text_length")
        )
        override_fields.add("max_text_length")

    if "MAX_FEATURE_FIELDS" in os.environ:
        overrides["max_feature_fields"] = _get_int_env(
            "MAX_FEATURE_FIELDS", base.get("max_feature_fields")
        )
        override_fields.add("max_feature_fields")

    if "MAX_JSON_BODY_BYTES" in os.environ:
        overrides["max_json_body_bytes"] = _get_int_env(
            "MAX_JSON_BODY_BYTES", base.get("max_json_body_bytes")
        )
        override_fields.add("max_json_body_bytes")

    if "RATE_LIMIT_PER_MINUTE" in os.environ:
        overrides["rate_limit_per_minute"] = _get_int_env(
            "RATE_LIMIT_PER_MINUTE", base.get("rate_limit_per_minute")
        )
        override_fields.add("rate_limit_per_minute")

    if "RATE_LIMIT_BURST" in os.environ:
        overrides["rate_limit_burst"] = _get_int_env(
            "RATE_LIMIT_BURST", base.get("rate_limit_burst")
        )
        override_fields.add("rate_limit_burst")

    if "CORS_TRUSTED_ORIGINS" in os.environ:
        overrides["cors_trusted_origins"] = _get_cors_trusted_origins()
        override_fields.add("cors_trusted_origins")

    return overrides, override_fields


def _settings_to_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name in _SETTINGS_FIELD_NAMES:
        if name not in data:
            continue
        value = data[name]
        if name in {"license_revoked_jtis", "license_revoked_subjects"}:
            payload[name] = sorted(_normalize_str_collection(value))
        elif name == "cors_trusted_origins":
            origins_payload: list[dict[str, Any]] = []
            for item in value or []:
                if isinstance(item, TrustedCORSOrigin):
                    origins_payload.append(
                        {
                            "origin": item.origin,
                            "allow_credentials": bool(item.allow_credentials),
                        }
                    )
                elif isinstance(item, dict):
                    origin = _normalize_optional_str(item.get("origin"))
                    if origin:
                        origins_payload.append(
                            {
                                "origin": origin,
                                "allow_credentials": bool(item.get("allow_credentials", False)),
                            }
                        )
                elif isinstance(item, str):
                    origin = item.strip()
                    if origin:
                        origins_payload.append({"origin": origin, "allow_credentials": False})
            payload[name] = origins_payload
        else:
            payload[name] = value
    return payload


def _load_settings_and_overrides() -> tuple[Settings, set[str]]:
    defaults = _settings_defaults()
    stored_raw = _settings_store.load()
    stored = _sanitize_store_data(stored_raw)
    data: dict[str, Any] = {**defaults, **stored}
    env_overrides, override_fields = _collect_env_overrides(data)
    data.update(env_overrides)
    settings_obj = Settings(**data)
    return settings_obj, override_fields


def _apply_settings(new_settings: Settings, overrides: set[str]) -> None:
    global _ENV_OVERRIDE_FIELDS
    for item in fields(Settings):
        setattr(settings, item.name, getattr(new_settings, item.name))
    _ENV_OVERRIDE_FIELDS = set(overrides)


def reload_settings() -> Settings:
    """Reload settings from disk and environment, mutating the shared instance."""

    new_settings, overrides = _load_settings_and_overrides()
    _apply_settings(new_settings, overrides)
    return settings


def update_persisted_settings(partial: dict[str, Any]) -> Settings:
    """Persist updated settings and refresh the in-memory configuration."""

    if not partial:
        return reload_settings()

    stored_raw = _settings_store.load()
    stored = _sanitize_store_data(stored_raw)
    for key, value in partial.items():
        if key in _SETTINGS_FIELD_NAMES:
            stored[key] = copy.deepcopy(value)

    payload = _settings_to_payload(stored)
    _settings_store.save(payload)
    return reload_settings()


def export_settings() -> dict[str, Any]:
    """Return a JSON-serializable representation of the active settings."""

    data: dict[str, Any] = {}
    for item in fields(Settings):
        value = getattr(settings, item.name)
        if item.name in {"license_revoked_jtis", "license_revoked_subjects"}:
            data[item.name] = sorted(value)
        elif item.name == "cors_trusted_origins":
            data[item.name] = [
                {"origin": origin.origin, "allow_credentials": origin.allow_credentials}
                for origin in value
            ]
        else:
            data[item.name] = value
    return data


def get_environment_overrides() -> dict[str, bool]:
    """Expose which fields are currently controlled by environment variables."""

    return {name: (name in _ENV_OVERRIDE_FIELDS) for name in _SETTINGS_FIELD_NAMES}


settings, _ENV_OVERRIDE_FIELDS = _load_settings_and_overrides()


__all__ = [
    "Settings",
    "TrustedCORSOrigin",
    "export_settings",
    "get_environment_overrides",
    "reload_settings",
    "settings",
    "update_persisted_settings",
]

