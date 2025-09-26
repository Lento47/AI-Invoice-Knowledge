from __future__ import annotations

import io
from statistics import fmean
from typing import Iterable

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from ai_invoice.schemas import OCRPage, OCRResult


_TESSERACT_CONFIG = "--oem 3 --psm 6"


def _page_confidence(confidences: Iterable[str]) -> float | None:
    """Compute the average confidence from the Tesseract output."""

    cleaned: list[float] = []
    for value in confidences:
        if not value or value == "-1":
            continue
        try:
            cleaned.append(float(value))
        except ValueError:
            continue
    if not cleaned:
        return None
    return float(fmean(cleaned))


def _image_to_page(img: Image.Image, page_number: int) -> OCRPage:
    text = pytesseract.image_to_string(img, config=_TESSERACT_CONFIG).strip()
    data = pytesseract.image_to_data(img, config=_TESSERACT_CONFIG, output_type=pytesseract.Output.DICT)
    confidence = _page_confidence(data.get("conf", []))
    width, height = img.size
    return OCRPage(
        page_number=page_number,
        text=text,
        confidence=confidence,
        width=int(width),
        height=int(height),
    )


def run_ocr(file_bytes: bytes) -> OCRResult:
    is_pdf = file_bytes[:5] == b"%PDF-"
    pages: list[OCRPage] = []
    if is_pdf:
        for index, page in enumerate(convert_from_bytes(file_bytes, dpi=300), start=1):
            pages.append(_image_to_page(page, index))
        source = "pdf"
    else:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        pages.append(_image_to_page(image, 1))
        source = "image"

    text = "\n\n".join(page.text for page in pages).strip()
    confidences = [page.confidence for page in pages if page.confidence is not None]
    average_confidence = float(fmean(confidences)) if confidences else None

    return OCRResult(
        source=source,
        text=text,
        average_confidence=average_confidence,
        pages=pages,
    )


def pdf_or_image_to_text(file_bytes: bytes) -> str:
    """Backward-compatible helper returning only the recognized text."""

    return run_ocr(file_bytes).text
