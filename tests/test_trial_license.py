from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_invoice.trial import TrialStatus, get_trial_status, resolve_trial_claims


@pytest.fixture(autouse=True)
def _reset_trial_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_INVOICE_TRIAL_PATH", str(tmp_path / "trial.json"))


def test_trial_status_initialized_on_first_call() -> None:
    start = datetime(2024, 1, 10, tzinfo=timezone.utc)
    status = get_trial_status(start)

    assert status.valid is True
    assert status.started_at == start
    assert status.expires_at == start + timedelta(days=7)

    path = Path(os.environ["AI_INVOICE_TRIAL_PATH"])
    assert path.exists()
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["started_at"].startswith("2024-01-10")


def test_trial_status_expires_after_seven_days() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    status = get_trial_status(start)
    assert status.valid is True

    expired = get_trial_status(start + timedelta(days=8))
    assert expired.valid is False
    assert expired.expires_at == status.expires_at


def test_resolve_trial_claims_returns_payload_when_valid() -> None:
    start = datetime(2024, 3, 1, tzinfo=timezone.utc)
    status, claims = resolve_trial_claims(start)
    assert isinstance(status, TrialStatus)
    assert claims is not None
    assert set(claims["features"]) == status.features


def test_resolve_trial_claims_returns_none_when_expired() -> None:
    start = datetime(2024, 2, 1, tzinfo=timezone.utc)
    status, _ = resolve_trial_claims(start)
    later = status.expires_at + timedelta(seconds=1)
    new_status, claims = resolve_trial_claims(later)
    assert new_status.valid is False
    assert claims is None
