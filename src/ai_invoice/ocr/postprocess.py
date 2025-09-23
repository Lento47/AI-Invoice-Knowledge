from __future__ import annotations

import re


def clean_text(txt: str) -> str:
    txt = txt.replace("\x0c", "\n").strip()
    return re.sub(r"[ \t]+", " ", txt)


def normalize_amount(txt: str) -> float | None:
    match = re.search(r"([\-]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))", txt)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))
