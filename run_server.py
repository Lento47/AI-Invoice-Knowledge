import os

import uvicorn

from ai_invoice.config import settings

if __name__ == "__main__":
    host = os.getenv("AI_INVOICE_HOST", "127.0.0.1")
    port = int(os.getenv("AI_INVOICE_PORT", "8088"))
    ssl_kwargs = {}
    if settings.tls_certfile_path and settings.tls_keyfile_path:
        ssl_kwargs["ssl_certfile"] = settings.tls_certfile_path
        ssl_kwargs["ssl_keyfile"] = settings.tls_keyfile_path
    uvicorn.run("api.main:app", host=host, port=port, **ssl_kwargs)
