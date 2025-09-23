"""Tests for the predictive prediction endpoints."""

from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from api.license_validator import LicenseClaims
from api.main import app, predict_endpoint
from api.routers.invoices import (
    PredictRequest,
    predict_from_features,
    predict_invoice_endpoint,
)
from ai_invoice.schemas import PredictiveResult

REQUIRED_FEATURE_KEYS = {
    "amount",
    "customer_age_days",
    "prior_invoices",
    "late_ratio",
    "weekday",
    "month",
}

VALID_FEATURES = {
    "amount": 950,
    "customer_age_days": 400,
    "prior_invoices": 12,
    "late_ratio": 0.2,
    "weekday": 2,
    "month": 9,
}


def _claims(*features: str) -> LicenseClaims:
    feature_list = list(features)
    return LicenseClaims(
        raw={"exp": 2_000_000_000, "jti": "unit-test", "features": feature_list},
        features=frozenset(feature_list),
    )


CLAIMS_PREDICT = _claims("predict")


@pytest.fixture(autouse=True)
def _stub_predict_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the predictive service call to avoid model dependencies."""

    def _fake_predict(features: dict) -> PredictiveResult:
        missing = REQUIRED_FEATURE_KEYS - set(features)
        if missing:
            raise ValueError(
                "Missing required feature columns: "
                + ", ".join(sorted(missing))
            )
        return PredictiveResult(
            predicted_payment_days=42.0,
            predicted_payment_date="2030-01-01",
            risk_score=0.5,
            confidence=0.9,
        )

    monkeypatch.setattr("api.routers.invoices.predict", _fake_predict)
    monkeypatch.setattr("api.main.predict_service", _fake_predict)


def test_predict_endpoint_registered_with_shared_response_model() -> None:
    routes = {
        route.path: route
        for route in app.routes
        if isinstance(route, APIRoute)
    }
    assert "/predict" in routes
    assert routes["/predict"].endpoint is predict_endpoint
    assert routes["/predict"].response_model is PredictiveResult


def test_predict_endpoints_return_same_result() -> None:
    request = PredictRequest(features=VALID_FEATURES)
    top_level = predict_endpoint(request, claims=CLAIMS_PREDICT)
    invoices_route = predict_invoice_endpoint(request, claims=CLAIMS_PREDICT)

    assert top_level == invoices_route


@pytest.mark.parametrize("callable_", [predict_endpoint, predict_invoice_endpoint])
def test_predict_endpoints_raise_http_400_for_invalid_features(callable_) -> None:
    request = PredictRequest(features={"amount": 100})
    with pytest.raises(HTTPException) as exc_info:
        callable_(request, claims=CLAIMS_PREDICT)

    assert exc_info.value.status_code == 400
    assert "Missing required feature columns" in exc_info.value.detail


def test_predict_request_requires_mapping_features() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(features="not-a-dict")


@pytest.mark.parametrize("callable_", [predict_endpoint, predict_invoice_endpoint])
def test_predict_endpoints_delegate_to_shared_helper(callable_) -> None:
    request = PredictRequest(features=VALID_FEATURES)
    result = callable_(request, claims=CLAIMS_PREDICT)

    assert isinstance(result, PredictiveResult)
    assert result == predict_from_features(VALID_FEATURES)


@pytest.mark.parametrize("callable_", [predict_endpoint, predict_invoice_endpoint])
def test_predict_endpoints_require_license_feature(callable_) -> None:
    request = PredictRequest(features=VALID_FEATURES)
    with pytest.raises(HTTPException) as exc_info:
        callable_(request, claims=_claims())

    assert exc_info.value.status_code == 403
    assert "License" in exc_info.value.detail

