from __future__ import annotations

import io

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image


def _img_to_text(img: Image.Image) -> str:
    return pytesseract.image_to_string(img, config="--oem 3 --psm 6")


def pdf_or_image_to_text(file_bytes: bytes) -> str:
    is_pdf = file_bytes[:5] == b"%PDF-"
    if is_pdf:
        pages = convert_from_bytes(file_bytes, dpi=300)
        return "\n\n".join(_img_to_text(page) for page in pages)
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    return _img_to_text(image)
