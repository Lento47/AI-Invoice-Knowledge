from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi import HTTPException

os.environ.setdefault("API_KEY", "pytest-default-key")

from ai_invoice import config
from ai_invoice.predictive import model as predictive_model
from api.routers import admin


def test_settings_persistence_with_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store_path = tmp_path / "settings.json"
    monkeypatch.setenv("AI_INVOICE_SETTINGS_PATH", str(store_path))
    monkeypatch.setenv("AI_API_KEY", "unit-api-key")
    config.reload_settings()

    assert config.settings.max_upload_bytes == 5 * 1024 * 1024
    config.update_persisted_settings({"max_upload_bytes": 123456})
    assert config.settings.max_upload_bytes == 123456

    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["max_upload_bytes"] == 123456

    # Environment overrides take precedence but do not replace persisted values
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "999")
    reloaded = config.reload_settings()
    assert reloaded.max_upload_bytes == 999
    overrides = config.get_environment_overrides()
    assert overrides["max_upload_bytes"] is True

    monkeypatch.delenv("MAX_UPLOAD_BYTES", raising=False)
    config.reload_settings()
    assert config.settings.max_upload_bytes == 123456

    # Restore baseline configuration for subsequent tests
    monkeypatch.delenv("AI_INVOICE_SETTINGS_PATH", raising=False)
    monkeypatch.setenv("AI_API_KEY", "pytest-default-key")
    config.reload_settings()


def test_admin_endpoints_apply_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store_path = tmp_path / "settings.json"
    monkeypatch.setenv("AI_INVOICE_SETTINGS_PATH", str(store_path))
    monkeypatch.setenv("AI_API_KEY", "integration-api-key")
    config.reload_settings()

    # Ensure authentication accepts the configured admin token
    admin.require_admin_token(x_admin_token="integration-api-key")

    envelope = admin.read_settings()
    assert envelope.values.api_key == "integration-api-key"

    updated_model = envelope.values.model_copy()
    updated_model.max_upload_bytes = 654321
    updated_model.cors_trusted_origins = [
        admin.CorsOriginModel(origin="https://unit.test", allow_credentials=False)
    ]
    updated_model.license_algorithm = "RS512"
    updated_model.admin_api_key = "rotated-admin"

    result = admin.update_settings(updated_model)
    assert result.values.max_upload_bytes == 654321
    assert result.values.admin_api_key == "rotated-admin"

    # Old token should no longer be accepted
    with pytest.raises(HTTPException):
        admin.require_admin_token(x_admin_token="integration-api-key")

    admin.require_admin_token(x_admin_token="rotated-admin")
    refreshed = admin.read_settings()
    assert refreshed.values.max_upload_bytes == 654321

    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["max_upload_bytes"] == 654321
    assert persisted["admin_api_key"] == "rotated-admin"

    # Reset to shared defaults so other tests see expected values
    monkeypatch.delenv("AI_INVOICE_SETTINGS_PATH", raising=False)
    monkeypatch.setenv("AI_API_KEY", "pytest-default-key")
    config.reload_settings()


def test_predictive_path_update_reflected_in_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_path = tmp_path / "settings.json"
    monkeypatch.setenv("AI_INVOICE_SETTINGS_PATH", str(store_path))
    monkeypatch.setenv("AI_API_KEY", "predictive-admin")
    config.reload_settings()

    envelope = admin.read_settings()
    updated = envelope.values.model_copy()
    new_model_path = tmp_path / "alternate" / "predictive.joblib"
    updated.predictive_path = str(new_model_path)

    result = admin.update_settings(updated)

    assert result.values.predictive_path == str(new_model_path)
    assert config.settings.predictive_path == str(new_model_path)

    pipeline = predictive_model.load_or_init()
    predictive_model.save_model(pipeline)

    assert new_model_path.exists()

    status = predictive_model.status()
    assert status["path"] == str(new_model_path)
    assert status["present"] is True

    reloaded = predictive_model.load_or_init()
    assert getattr(reloaded, "feature_columns", None) == getattr(
        pipeline, "feature_columns", None
    )

    monkeypatch.delenv("AI_INVOICE_SETTINGS_PATH", raising=False)
    monkeypatch.setenv("AI_API_KEY", "pytest-default-key")
    config.reload_settings()
