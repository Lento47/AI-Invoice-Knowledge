from __future__ import annotations

from pathlib import Path


def is_pdf(data: bytes) -> bool:
    """Quick heuristic to detect if a byte payload represents a PDF file."""
    return data[:5] == b"%PDF-"


def load_pdf_bytes(path: str | Path) -> bytes:
    return Path(path).expanduser().read_bytes()
