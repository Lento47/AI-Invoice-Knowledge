---

# AI Invoice System

This repository contains a cross-platform AI service (Python/FastAPI) and Windows-focused .NET integration for automated invoice OCR, data extraction, smart classification, and payment prediction.

## Project layout

```
.
├─ README.md
├─ .env.example
├─ pyproject.toml
├─ models/
│  ├─ classifier.joblib
│  └─ predictive.joblib
├─ data/
│  ├─ samples/
│  └─ training/
├─ src/
│  ├─ ai_invoice/
│  │  ├─ config.py
│  │  ├─ schemas.py
│  │  ├─ service.py
│  │  ├─ utils/
│  │  │  ├─ io.py
│  │  │  └─ pdf.py
│  │  ├─ ocr/
│  │  │  ├─ engine.py
│  │  │  └─ postprocess.py
│  │  ├─ nlp_extract/
│  │  │  ├─ rules.py
│  │  │  └─ parser.py
│  │  ├─ classify/
│  │  │  ├─ featurize.py
│  │  │  └─ model.py
│  │  └─ predictive/
│  │     ├─ features.py
│  │     └─ model.py
│  └─ api/
│     ├─ main.py
│     ├─ middleware.py
│     └─ routers/
│        ├─ health.py
│        ├─ invoices.py
│        └─ models.py
└─ dotnet/
   ├─ AIInvoiceSystem.sln
   ├─ AIInvoiceSystem.API/
   └─ AIInvoiceSystem.Core/
```

## Python service

1. Create a virtual environment and install dependencies (via `uv` or `pip`).

   ```bash
   uv sync
   # or
   python -m venv .venv && source .venv/bin/activate
   pip install -e .
   ```

2. Copy `.env.example` to `.env` if you want to override model paths.

3. Start the API locally:

   ```bash
   uv run uvicorn api.main:app --reload --port 8088
   # or
   python -m uvicorn api.main:app --reload --port 8088
   ```

4. Test the endpoints:

   ```bash
   curl http://localhost:8088/health/
   curl -F "file=@data/samples/invoice1.pdf" http://localhost:8088/invoices/extract
   curl -H "Content-Type: application/json" -d '{"text":"ACME INVOICE #F-1002 ..."}' http://localhost:8088/invoices/classify
   curl -H "Content-Type: application/json" -d '{"features":{"amount":950,"customer_age_days":400,"prior_invoices":12,"late_ratio":0.2,"weekday":2,"month":9}}' http://localhost:8088/invoices/predict
   curl -H "Content-Type: application/json" -d '{"features":{"amount":950,"customer_age_days":400,"prior_invoices":12,"late_ratio":0.2,"weekday":2,"month":9}}' http://localhost:8088/predict

   # /predict is a lightweight alias of /invoices/predict with the same schema and response.
   ```

5. (Optional) Interact with the classifier management endpoints:

   ```bash
   curl http://localhost:8088/models/classifier/status
   curl -F "file=@data/training/classifier_example.csv" http://localhost:8088/models/classifier/train
   curl -H "Content-Type: application/json" -d '{"text":"POS RECEIPT Store 123 Total 11.82"}' http://localhost:8088/models/classifier/classify
   ```

### Windows packaging

Install Tesseract OCR and Poppler for PDF rendering, then bundle the FastAPI server with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --name ai_invoice_api --add-data "models;models" -p src --collect-all spacy --collect-all sklearn run_server.py
```

The resulting executable can be shipped alongside the .NET desktop app. Have the Windows app start the executable and wait for `GET /health/` to return `{"ok": true}` before making requests.

## .NET integration

The `dotnet/` folder contains a solution with two projects:

* **AIInvoiceSystem.Core** – class library with DTOs and an `AIClient` wrapper for the FastAPI service.
* **AIInvoiceSystem.API** – minimal ASP.NET Core project demonstrating dependency registration.

Restore and build:

```powershell
cd dotnet
dotnet restore
dotnet build
```

Add the HTTP client in `Program.cs`:

```csharp
builder.Services.AddHttpClient<AIClient>(c => c.BaseAddress = new Uri("http://localhost:8088"));
```

Then inject and use `AIClient` in your controllers or background services.

## Next steps

* Enhance OCR with layout-aware parsing.
* Expand NLP rules and add locale-aware total extraction.
* Broaden the dataset and labels for the classifier and predictive models.
* Add retries, telemetry, and circuit breakers on the .NET side.
