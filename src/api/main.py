from __future__ import annotations

from fastapi import FastAPI

from .middleware import configure_middleware
from .routers import health, invoices, models

app = FastAPI(title="AI Invoice System")
configure_middleware(app)
app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(models.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Invoice System API"}
