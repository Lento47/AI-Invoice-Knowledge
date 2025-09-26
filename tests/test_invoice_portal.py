"""Integration tests for the invoice portal template and assets."""

import asyncio
import os
import sys
from pathlib import Path

from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from starlette.templating import _TemplateResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

os.environ.setdefault("API_KEY", "portal-test-secret")

from api.license_validator import LicenseClaims  # noqa: F401
from api.main import app, invoice_portal  # noqa: E402  pylint: disable=wrong-import-position

# Optional customs/TICA module (only present if that feature is enabled)
try:
    from api.routers import tica  # noqa: F401
except ImportError:
    tica = None


client = TestClient(app)


def _build_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/portal",
        "root_path": "",
        "app": app,
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }
    return Request(scope)


def test_invoice_portal_template_served() -> None:
    request = _build_request()
    response = invoice_portal(request)

    assert isinstance(response, _TemplateResponse)
    assert response.template.name == "invoice_portal.html"
    assert response.context["request"] is request

    rendered = response.body.decode("utf-8")
    assert "Invoice Operations Portal" in rendered
    assert "/static/js/invoice_portal.js" in rendered

    # If the optional customs/TICA module is enabled, the portal should include its panel.
    if tica is not None:
        assert "TICA Customs PDF" in rendered
        assert 'id="tica-form"' in rendered


def test_invoice_portal_static_asset_paths_resolve() -> None:
    css_path = app.url_path_for("static", path="css/invoice_portal.css")
    js_path = app.url_path_for("static", path="js/invoice_portal.js")

    assert css_path == "/static/css/invoice_portal.css"
    assert js_path == "/static/js/invoice_portal.js"

    css_file = PROJECT_ROOT / "src" / "api" / "static" / "css" / "invoice_portal.css"
    js_file = PROJECT_ROOT / "src" / "api" / "static" / "js" / "invoice_portal.js"

    assert css_file.exists()
    assert js_file.exists()


def test_portal_accessible_without_api_key() -> None:
    response = client.get("/portal")

    assert response.status_code == 200
    assert "Invoice Operations Portal" in response.text


def test_static_asset_accessible_without_api_key() -> None:
    response = client.get("/static/css/invoice_portal.css")

    assert response.status_code == 200
    assert "invoice-portal" in response.text


def test_protected_api_routes_still_require_api_key() -> None:
    response = client.get("/models/classifier/status")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}

    authed = client.get(
        "/models/classifier/status",
        headers={"X-API-Key": os.environ["API_KEY"]},
    )

    assert authed.status_code == 401
    assert authed.json() == {"detail": "License token is required."}


async def _collect_body(response: StreamingResponse) -> bytes:
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    return b"".join(chunks)


def test_tica_pdf_generation_returns_pdf() -> None:
    # Optional module: if not enabled, skip this test silently.
    if tica is None:
        return

    payload = tica.TicaInvoicePayload(
        invoice_number="TICA-001",
        issue_date="2024-06-01",
        exporter_name="Exportadora Centroamericana",
        exporter_id="301230123",
        exporter_address="San José, Costa Rica",
        importer_name="Cliente Internacional",
        importer_id="99887766",
        importer_address="Panamá City, Panamá",
        incoterm="FOB",
        transport_mode="Marítimo",
        destination_port="Puerto Moín",
        currency="USD",
        subtotal=5000,
        tax=650,
        total=5650,
        items=[
            tica.TicaInvoiceItem(
                description="Equipo médico especializado",
                quantity=5,
                unit_value=1000,
                hs_code="9018.90",
                country_of_origin="DE",
            )
        ],
    )

    claims = LicenseClaims(raw={"features": ["extract"]}, features=frozenset({"extract"}))
    response = tica.generate_tica_invoice_pdf(payload, claims)

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "application/pdf"
    disposition = response.headers.get("Content-Disposition", "")
    assert "tica_invoice_TICA-001.pdf" in disposition

    body = asyncio.run(_collect_body(response))
    assert body.startswith(b"%PDF")
    assert len(body) > 500

