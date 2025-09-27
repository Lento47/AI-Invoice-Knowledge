import os

import uvicorn

from ai_invoice.config import settings

if __name__ == "__main__":
    host = os.getenv("AI_INVOICE_HOST", "127.0.0.1")
    port = int(os.getenv("AI_INVOICE_PORT", "8088"))
    uvicorn.run("api.main:app", host=host, port=port)
