from __future__ import annotations

import re

from .rules import PATTERNS, first_regex
from ..ocr.postprocess import clean_text, normalize_amount
from ..schemas import InvoiceExtraction, LineItem


def parse_structured(raw: str) -> InvoiceExtraction:
    txt = clean_text(raw)
    invoice_number = first_regex(txt, PATTERNS["invoice_number"])
    invoice_date = first_regex(txt, PATTERNS["invoice_date"])
    due_date = first_regex(txt, PATTERNS["due_date"])
    tax_id = first_regex(txt, PATTERNS["tax_id"])

    totals = [normalize_amount(match.group(0))
              for match in re.finditer(r"(total\s*[: ]\s*[0-9\.,]{3,})", txt, flags=re.IGNORECASE)]
    total = totals[-1] if totals else None

    items: list[LineItem] = []
    for line in txt.splitlines():
        match = re.search(r"(.+?)\s+(\d+(?:\.\d+)?)\s+x\s+(\d+(?:\.\d+)?)\s+=\s+(\d+(?:\.\d+)?)", line)
        if match:
            desc, qty, unit, line_total = match.groups()
            items.append(
                LineItem(
                    description=desc.strip(),
                    quantity=float(qty),
                    unit_price=float(unit),
                    total=float(line_total),
                )
            )

    return InvoiceExtraction(
        supplier_name=None,
        supplier_tax_id=tax_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        currency="USD",
        subtotal=None,
        tax=None,
        total=total,
        buyer_name=None,
        buyer_tax_id=None,
        items=items,
        raw_text=txt,
    )
