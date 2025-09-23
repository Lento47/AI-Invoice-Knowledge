from __future__ import annotations

import asyncio
import io
import os
import sys
from pathlib import Path
from typing import Iterable

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.datastructures import UploadFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

os.environ.setdefault("API_KEY", "test-secret")

import ai_invoice.predictive.model as predictive_model
from src.api.main import app
from src.api.routers import predictive as predictive_router


def _get_route(path: str, method: str) -> APIRoute:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method.upper() in (route.methods or {}):
            return route
    available: Iterable[tuple[str, Iterable[str] | None]] = (
        (route.path, route.methods) for route in app.routes if isinstance(route, APIRoute)
    )
    raise AssertionError(f"Route {method} {path} not registered. Available: {list(available)}")


@pytest.fixture()
def temp_predictive_model_path(tmp_path, monkeypatch):
    model_path = tmp_path / "predictive.joblib"
    monkeypatch.setattr(predictive_model, "MODEL_PATH", str(model_path))
    yield
    if model_path.exists():
        model_path.unlink()


def test_predictive_status_route_registered(temp_predictive_model_path) -> None:
    route = _get_route("/models/predictive/status", "GET")
    payload = route.endpoint()
    assert isinstance(payload, dict)
    assert {"present", "path"}.issubset(payload)


def test_predictive_predict_route_registered(temp_predictive_model_path, monkeypatch) -> None:
    route = _get_route("/models/predictive/predict", "POST")

    captured: dict[str, dict[str, float | int]] = {}

    def fake_predict(features: dict[str, float | int]) -> dict[str, float]:
        captured["features"] = features
        return {"predicted_days": 12.5}

    monkeypatch.setattr(predictive_router, "predict_payment_days", fake_predict)

    body = predictive_router.PredictIn(
        amount=2500.0,
        customer_age_days=365,
        prior_invoices=5,
        late_ratio=0.1,
        weekday=2,
        month=6,
    )
    payload = route.endpoint(body)
    assert isinstance(payload, dict)
    assert payload == {"predicted_days": 12.5}
    assert captured["features"]["amount"] == 2500.0


def test_predictive_train_route_registered(temp_predictive_model_path, monkeypatch) -> None:
    route = _get_route("/models/predictive/train", "POST")

    header = "amount,customer_age_days,prior_invoices,late_ratio,weekday,month,actual_payment_days"
    rows = [
        f"{1000 + idx},{30 + idx},{idx % 5},{min(0.9, 0.05 * idx)},{idx % 7},{(idx % 12) + 1},{20 + idx}"
        for idx in range(24)
    ]
    csv_bytes = "\n".join([header, *rows]).encode()
    upload = UploadFile(filename="train.csv", file=io.BytesIO(csv_bytes))

    def fake_train(csv_payload: bytes) -> dict[str, object]:
        assert csv_payload.startswith(b"amount,customer_age_days")
        return {"count_train": 20, "metrics": {"mae": 1.2}}

    monkeypatch.setattr(predictive_router, "train_from_csv_bytes", fake_train)

    async def invoke() -> dict[str, object]:
        return await route.endpoint(file=upload)

    payload = asyncio.run(invoke())
    assert isinstance(payload, dict)
    assert payload.get("ok") is True
    assert "metrics" in payload


def test_predictive_train_rejects_empty_upload(temp_predictive_model_path) -> None:
    route = _get_route("/models/predictive/train", "POST")

    upload = UploadFile(filename="empty.csv", file=io.BytesIO(b""))

    async def invoke() -> dict[str, object]:
        return await route.endpoint(file=upload)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(invoke())

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Uploaded file is empty."
