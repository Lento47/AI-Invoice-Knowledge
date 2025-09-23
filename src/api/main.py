from __future__ import annotations

import logging
import sys

from fastapi import FastAPI

from .middleware import configure_middleware
from .routers import health, invoices, models

# Basic stdout logging
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers = [handler]
root_logger.setLevel(logging.INFO)

app = FastAPI(title="AI Invoice System")
configure_middleware(app)

# Routers:
# - /health/      -> health.router
# - /invoices/*   -> invoices.router (extract, classify, predict)
# - /models/*     -> models.router (classifier status/train/classify)
app.include_router(health.router)
app.include_router(invoices.router)
app.include_router(models.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Invoice System API"}
