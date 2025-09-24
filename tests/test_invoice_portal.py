"""Integration tests for the invoice portal template and assets."""

from pathlib import Path
import os
import sys

from fastapi import Request
from starlette.templating import _TemplateResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

os.environ.setdefault("API_KEY", "portal-test-secret")

from api.main import app, invoice_portal  # noqa: E402  pylint: disable=wrong-import-position


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


def test_invoice_portal_static_asset_paths_resolve() -> None:
    css_path = app.url_path_for("static", path="css/invoice_portal.css")
    js_path = app.url_path_for("static", path="js/invoice_portal.js")

    assert css_path == "/static/css/invoice_portal.css"
    assert js_path == "/static/js/invoice_portal.js"

    css_file = PROJECT_ROOT / "src" / "api" / "static" / "css" / "invoice_portal.css"
    js_file = PROJECT_ROOT / "src" / "api" / "static" / "js" / "invoice_portal.js"

    assert css_file.exists()
    assert js_file.exists()
