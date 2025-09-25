"""Helpers for managing the out-of-the-box 7-day trial license."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

_DEFAULT_FEATURES = frozenset(
    {
        "extract",
        "classify",
        "predict",
        "predictive",
        "predictive_train",
        "train",
    }
)

_TRIAL_DURATION = timedelta(days=7)


def _trial_store_path() -> Path:
    override = os.getenv("AI_INVOICE_TRIAL_PATH")
    if override:
        return Path(override).expanduser()
    return Path("data/trial_license.json")


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class TrialStatus:
    """Represents the persisted trial window for a local installation."""

    started_at: datetime
    expires_at: datetime
    valid: bool
    features: frozenset[str]

    def as_claims(self) -> Mapping[str, object]:
        return {
            "sub": "trial",  # pseudo subject identifying the trial user
            "jti": f"trial-{int(self.started_at.timestamp())}",
            "exp": int(self.expires_at.timestamp()),
            "features": sorted(self.features),
            "trial": True,
        }


def _persist_trial(started_at: datetime, expires_at: datetime) -> None:
    payload = {
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
    }
    path = _trial_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _initialize_trial(now: datetime) -> TrialStatus:
    expires_at = now + _TRIAL_DURATION
    _persist_trial(now, expires_at)
    return TrialStatus(
        started_at=now,
        expires_at=expires_at,
        valid=True,
        features=_DEFAULT_FEATURES,
    )


def _load_trial(now: datetime) -> TrialStatus:
    path = _trial_store_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        started = _parse_timestamp(raw["started_at"])
        expires = _parse_timestamp(raw["expires_at"])
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return _initialize_trial(now)

    if expires <= started:
        return _initialize_trial(now)

    is_valid = now < expires
    return TrialStatus(
        started_at=started,
        expires_at=expires,
        valid=is_valid,
        features=_DEFAULT_FEATURES,
    )


def get_trial_status(now: datetime | None = None) -> TrialStatus:
    """Return the current trial status, creating one if needed."""

    current_time = now.astimezone(timezone.utc) if isinstance(now, datetime) else datetime.now(timezone.utc)
    path = _trial_store_path()
    if not path.exists():
        return _initialize_trial(current_time)
    return _load_trial(current_time)


def resolve_trial_claims(now: datetime | None = None) -> tuple[TrialStatus, Mapping[str, object] | None]:
    """Return the persisted trial status and, when active, claim payload."""

    status = get_trial_status(now)
    if status.valid:
        return status, status.as_claims()
    return status, None


__all__ = ["TrialStatus", "get_trial_status", "resolve_trial_claims"]
