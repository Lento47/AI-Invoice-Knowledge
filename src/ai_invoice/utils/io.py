from pathlib import Path
from typing import BinaryIO


def read_bytes(source: str | Path | BinaryIO) -> bytes:
    """Load bytes from a path or binary stream."""
    if hasattr(source, "read"):
        return source.read()
    return Path(source).expanduser().read_bytes()


def write_bytes(target: str | Path, data: bytes) -> None:
    """Persist bytes to disk, ensuring parent directories exist."""
    path = Path(target).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
