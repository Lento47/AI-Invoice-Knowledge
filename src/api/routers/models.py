from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/train")
def trigger_training() -> dict[str, str]:
    return {"status": "not_implemented"}
