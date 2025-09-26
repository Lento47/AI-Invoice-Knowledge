from __future__ import annotations

import re


def clean_text(txt: str) -> str:
    txt = txt.replace("\x0c", "\n").strip()
    return re.sub(r"[ \t]+", " ", txt)


def _separators(number: str) -> tuple[str | None, str | None]:
    """Infer decimal and thousands separators for *number*.

    When both a comma and a dot are present we assume the last separator is the
    decimal marker. With only a single separator we treat it as a decimal marker
    if it is followed by exactly two digits, otherwise it is classified as a
    thousands separator.
    """

    comma_pos = number.rfind(",")
    dot_pos = number.rfind(".")

    if comma_pos != -1 and dot_pos != -1:
        if comma_pos > dot_pos:
            return ",", "."
        return ".", ","

    if comma_pos != -1:
        decimals = len(number) - comma_pos - 1
        if decimals == 2:
            return ",", None
        return None, ","

    if dot_pos != -1:
        decimals = len(number) - dot_pos - 1
        if decimals == 2:
            return ".", None
        return None, "."

    return None, None


def normalize_amount(txt: str) -> float | None:
    match = re.search(
        r"([\-]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|[\-]?\d+(?:[.,]\d{2}))",
        txt,
    )
    if not match:
        return None

    number = match.group(1)
    number = number.replace(" ", "")

    decimal_sep, thousands_sep = _separators(number)

    if thousands_sep:
        number = number.replace(thousands_sep, "")

    if decimal_sep and decimal_sep != ".":
        number = number.replace(decimal_sep, ".")
    elif not decimal_sep:
        number = number.replace(",", "").replace(".", "")

    try:
        return float(number)
    except ValueError:
        return None
