from __future__ import annotations

import os
import sys
from pathlib import Path

from types import SimpleNamespace

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

os.environ.setdefault("API_KEY", "test-secret")

from api.main import app  # noqa: E402
from api.license_validator import HEADER_NAME  # noqa: E402
from api.security import require_license_token  # noqa: E402


client = TestClient(app)


def _mock_license_dependency(request):  # type: ignore[override]
    payload = SimpleNamespace(
        tenant=SimpleNamespace(id="test-tenant"),
        features=["workspace"],
        token_id="unit-test-token",
    )
    request.state.license_payload = payload
    return payload


app.dependency_overrides[require_license_token] = _mock_license_dependency

HEADERS = {
    "X-API-Key": os.environ["API_KEY"],
    HEADER_NAME: "unit-test-license",
}


def test_workspace_dashboard_payload() -> None:
    response = client.get("/workspace/dashboard", headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert {"cards", "cash_flow"} <= payload.keys()
    assert isinstance(payload["cards"], list)
    assert isinstance(payload["cash_flow"], list)
    assert any(card["label"] == "Pending Approvals" for card in payload["cards"])


def test_workspace_invoice_payload() -> None:
    response = client.get("/workspace/invoice", headers=HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["id"] == "INV-2098"
    assert len(payload["line_items"]) >= 1


def test_workspace_approvals_update_cycle() -> None:
    initial = client.get("/workspace/approvals", headers=HEADERS)
    assert initial.status_code == 200
    items = initial.json()
    target = items[0]

    decision = client.post(
        f"/workspace/approvals/{target['id']}",
        json={"status": "Approved"},
        headers=HEADERS,
    )
    assert decision.status_code == 200
    updated = decision.json()
    assert updated["status"] == "Approved"

    # Unknown approvals should surface a 404 so the UI can revert optimistic updates
    missing = client.post(
        "/workspace/approvals/unknown",
        json={"status": "Rejected"},
        headers=HEADERS,
    )
    assert missing.status_code == 404
