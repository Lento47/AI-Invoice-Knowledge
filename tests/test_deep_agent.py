from __future__ import annotations

import json

from ai_invoice.agents import (
    DEFAULT_INVOICE_AGENT_INSTRUCTIONS,
    create_invoice_deep_agent,
)
from ai_invoice.agents import deep_agent as deep_module
from ai_invoice.config import settings
from ai_invoice.schemas import (
    ClassificationResult,
    InvoiceExtraction,
    LineItem,
    PredictiveResult,
)


def test_create_invoice_deep_agent_uses_settings_model(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_model", "stub-model", raising=False)

    captured: dict[str, object] = {}

    def _fake_create_deep_agent(tools, instructions, **kwargs):
        captured["tools"] = tools
        captured["instructions"] = instructions
        captured["kwargs"] = kwargs
        return {"graph": "fake"}

    monkeypatch.setattr(deep_module, "_resolve_deep_agent_factory", lambda: _fake_create_deep_agent)

    agent = create_invoice_deep_agent()

    assert agent == {"graph": "fake"}
    assert captured["instructions"] == DEFAULT_INVOICE_AGENT_INSTRUCTIONS
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs.get("model") == "stub-model"
    tool_names = {tool.__name__ for tool in captured["tools"]}
    assert {"parse_invoice_text", "classify_invoice_text", "predict_invoice_payment"} <= tool_names


def test_invoice_agent_tools_return_serializable_payload(monkeypatch) -> None:
    extraction = InvoiceExtraction(
        supplier_name="ACME",
        supplier_tax_id="123",
        invoice_number="INV-1",
        invoice_date="2024-01-01",
        due_date="2024-01-31",
        currency="USD",
        subtotal=100.0,
        tax=10.0,
        total=110.0,
        buyer_name="Widgets Inc",
        buyer_tax_id="321",
        items=[
            LineItem(description="Gadget", quantity=1, unit_price=100.0, total=100.0),
        ],
        raw_text="ACME invoice",
    )

    classification = ClassificationResult(label="invoice", proba=0.95)
    prediction = PredictiveResult(
        predicted_payment_days=12.0,
        predicted_payment_date="2024-02-12",
        risk_score=0.2,
        confidence=0.8,
    )

    monkeypatch.setattr("ai_invoice.nlp_extract.parser.parse_structured", lambda raw: extraction)
    monkeypatch.setattr("ai_invoice.service.classify_text", lambda raw: classification)
    monkeypatch.setattr("ai_invoice.service.predict", lambda features: prediction)

    assert deep_module.parse_invoice_text("raw") == extraction.model_dump()
    assert deep_module.classify_invoice_text("raw") == classification.model_dump()

    payload = {
        "amount": 110.0,
        "customer_age_days": 365,
        "prior_invoices": 10,
        "late_ratio": 0.1,
        "weekday": 2,
        "month": 4,
    }
    result = deep_module.predict_invoice_payment(json.dumps(payload))
    assert result == prediction.model_dump()
