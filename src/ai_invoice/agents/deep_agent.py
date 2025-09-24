"""LangGraph Deep Agent integration for the AI Invoice system."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping, Sequence

try:
    from deepagents import create_deep_agent as _deepagents_create_deep_agent
except ImportError:  # pragma: no cover - dependency guard
    _deepagents_create_deep_agent = None

from ai_invoice import service
from ai_invoice.config import settings
from ai_invoice.nlp_extract import parser

DEFAULT_INVOICE_AGENT_INSTRUCTIONS = """You orchestrate automated invoice workflows for finance teams.
Your goal is to plan multi-step solutions that combine OCR'd invoice text, 
classification, and payment forecasting so that accountants receive clean, 
actionable answers.

You can use these domain tools:

- `parse_invoice_text(raw_invoice_text: str)` → Extract structured invoice
  fields (supplier, totals, dates, line items) from raw OCR text. Always pass
  cleaned text – this tool does not open PDFs directly.
- `classify_invoice_text(raw_invoice_text: str)` → Categorise invoice or expense
  narratives into supported business labels. Use this to validate document
  intent or route work to the right queue.
- `predict_invoice_payment(features: dict)` → Forecast when an invoice will be
  paid. Supply a JSON object with keys `amount`, `customer_age_days`,
  `prior_invoices`, `late_ratio`, `weekday`, and `month`.

General guidance:
- Break down complex requests with the planning tool before calling domain
  tools.
- Ask the user to supply OCR text or upload files to the virtual file system if
  you cannot find the required information.
- Record important outputs in files so future steps (or the user) can reuse
  them.
- Finish with a concise summary that cites which tools produced each key
  insight.
"""


def parse_invoice_text(raw_invoice_text: str) -> Mapping[str, Any]:
    """Parse raw OCR text into structured invoice fields.

    Args:
        raw_invoice_text: Cleaned invoice text extracted from OCR or another
            upstream system. The text should already be human-readable – this
            helper does not accept binary PDF or image bytes.

    Returns:
        A dictionary compatible with :class:`ai_invoice.schemas.InvoiceExtraction`.
    """

    extraction = parser.parse_structured(raw_invoice_text)
    return extraction.model_dump()


def classify_invoice_text(raw_invoice_text: str) -> Mapping[str, Any]:
    """Run the classifier on the supplied invoice or receipt text."""

    result = service.classify_text(raw_invoice_text)
    return result.model_dump()


def predict_invoice_payment(features: Mapping[str, Any] | str) -> Mapping[str, Any]:
    """Predict payment timing based on engineered invoice features.

    The deep agent may call this tool with either a dictionary or a JSON string.
    The payload must include the six canonical predictive features used by the
    REST API: ``amount``, ``customer_age_days``, ``prior_invoices``,
    ``late_ratio``, ``weekday``, and ``month``.
    """

    if isinstance(features, str):
        try:
            payload = json.loads(features)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ValueError("predict_invoice_payment requires JSON features") from exc
    else:
        try:
            payload = dict(features)
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValueError("predict_invoice_payment requires a mapping of features") from exc

    if not isinstance(payload, Mapping):  # pragma: no cover - defensive
        raise ValueError("predict_invoice_payment requires a mapping of features")

    result = service.predict(dict(payload))
    return result.model_dump()


def _compose_instructions(extra_instructions: str | None) -> str:
    if not extra_instructions:
        return DEFAULT_INVOICE_AGENT_INSTRUCTIONS
    cleaned = extra_instructions.strip()
    if not cleaned:
        return DEFAULT_INVOICE_AGENT_INSTRUCTIONS
    return "\n\n".join(
        (
            DEFAULT_INVOICE_AGENT_INSTRUCTIONS,
            "Additional operator guidance:",
            cleaned,
        )
    )


def _extend_tools(default_tools: Sequence[Callable[..., Any]], extras: Iterable[Callable[..., Any]] | None) -> list[Callable[..., Any]]:
    combined = list(default_tools)
    if not extras:
        return combined
    for tool in extras:
        if tool not in combined:
            combined.append(tool)
    return combined


def _resolve_deep_agent_factory() -> Callable[..., Any]:
    if _deepagents_create_deep_agent is None:
        raise RuntimeError(
            "deepagents is not installed. Install the optional dependency with `pip install deepagents` to create invoice agents."
        )
    return _deepagents_create_deep_agent


def create_invoice_deep_agent(
    *,
    extra_tools: Iterable[Callable[..., Any]] | None = None,
    instructions: str | None = None,
    model: Any | None = None,
    subagents: Sequence[Mapping[str, Any]] | None = None,
    **kwargs: Any,
):
    """Create a deep agent wired to the invoice automation toolset.

    Args:
        extra_tools: Optional additional LangChain-compatible tools to expose to
            the agent alongside the built-in invoice helpers.
        instructions: Extra instructions appended to the default operator brief.
        model: Optional model override. When omitted the value from settings
            (``settings.agent_model``) is used, falling back to the deepagents
            default if still unset.
        subagents: Optional deepagents sub-agent definitions.
        **kwargs: Additional keyword arguments forwarded to
            :func:`deepagents.create_deep_agent`.
    """

    default_tools: Sequence[Callable[..., Any]] = (
        parse_invoice_text,
        classify_invoice_text,
        predict_invoice_payment,
    )
    tools = _extend_tools(default_tools, extra_tools)
    prompt = _compose_instructions(instructions)

    agent_kwargs: dict[str, Any] = dict(kwargs)
    if subagents is not None:
        agent_kwargs["subagents"] = list(subagents)

    configured_model = model if model is not None else getattr(settings, "agent_model", None)
    if configured_model is not None:
        agent_kwargs["model"] = configured_model

    factory = _resolve_deep_agent_factory()
    return factory(tools, prompt, **agent_kwargs)


__all__ = [
    "DEFAULT_INVOICE_AGENT_INSTRUCTIONS",
    "classify_invoice_text",
    "create_invoice_deep_agent",
    "parse_invoice_text",
    "predict_invoice_payment",
]

