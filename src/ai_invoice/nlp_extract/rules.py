from __future__ import annotations

import re
from typing import Optional


PATTERNS = {
    "invoice_number": r"(?:invoice|factura|bill)\s*[:#\- ]\s*([A-Z0-9\-\/]+)",
    "invoice_date": r"(?:date|fecha)\s*[: ]\s*([0-9]{2,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{1,2})",
    "due_date": r"(?:due|vencimiento)\s*[: ]\s*([0-9]{2,4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{1,2})",
    "tax_id": r"(?:tax id|ruc|rif|nit|nif)\s*[:# ]\s*([A-Z0-9\-\.]+)",
}


def first_regex(txt: str, pat: str) -> Optional[str]:
    match = re.search(pat, txt, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None
