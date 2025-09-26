from __future__ import annotations

from ai_invoice.nlp_extract.parser import parse_structured
from ai_invoice.ocr.postprocess import normalize_amount


def test_normalize_amount_us_format():
    assert normalize_amount("Total 1,234.56") == 1234.56


def test_normalize_amount_eu_format():
    assert normalize_amount("Total 1.234,56") == 1234.56


def test_parse_structured_uses_normalized_total_us():
    extraction = parse_structured("Invoice\nTotal: 1,234.56")
    assert extraction.total == 1234.56


def test_parse_structured_uses_normalized_total_eu():
    extraction = parse_structured("Invoice\nTotal: 1.234,56")
    assert extraction.total == 1234.56
