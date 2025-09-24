"""Persistence backend for configuration settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class SettingsStore:
    """Simple JSON-backed settings repository."""

    def __init__(self, *, default_path: str | Path | None = None) -> None:
        base_path = default_path or "data/settings.json"
        self._default_path = Path(base_path)

    @property
    def path(self) -> Path:
        """Resolve the active settings path, honoring environment overrides."""

        override = os.getenv("AI_INVOICE_SETTINGS_PATH")
        if override and override.strip():
            return Path(override).expanduser()
        return self._default_path

    def load(self) -> dict[str, Any]:
        """Load persisted settings, returning an empty mapping if missing."""

        target = self.path
        if not target.exists():
            return {}
        try:
            with target.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Settings file at {target} is not valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Settings file must contain a JSON object at the top level.")
        return data

    def save(self, payload: dict[str, Any]) -> None:
        """Persist settings atomically to disk."""

        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(target.parent), delete=False
        ) as handle:
            handle.write(serialized)
            handle.write("\n")
            temp_name = handle.name
        os.replace(temp_name, target)


__all__ = ["SettingsStore"]

