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
│  ├─ ai\_invoice/
│  │  ├─ config.py
│  │  ├─ schemas.py
│  │  ├─ service.py
│  │  ├─ utils/
│  │  │  ├─ io.py
│  │  │  └─ pdf.py
│  │  ├─ ocr/
│  │  │  ├─ engine.py
│  │  │  └─ postprocess.py
│  │  ├─ nlp\_extract/
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

````

## Python service

1. Create a virtual environment and install dependencies (via `uv` or `pip`):

   ```bash
   uv sync
   # or
   python -m venv .venv && source .venv/bin/activate
   pip install -e .
````

2. Copy `.env.example` to `.env` if you want to override model paths or configure authentication/limits.

3. Start the API locally:

   ```bash
   uv run uvicorn api.main:app --reload --port 8088
   # or
   python -m uvicorn api.main:app --reload --port 8088
   ```

4. Test the endpoints (remember to include your `X-API-Key` header on authenticated routes):

   ```bash
   curl http://localhost:8088/health/
   curl -H "X-API-Key: $AI_API_KEY" -F "file=@data/samples/invoice1.pdf" http://localhost:8088/invoices/extract
   curl -H "X-API-Key: $AI_API_KEY" -H "Content-Type: application/json" -d '{"text":"ACME INVOICE #F-1002 ..."}' http://localhost:8088/invoices/classify
   curl -H "X-API-Key: $AI_API_KEY" -H "Content-Type: application/json" -d '{"features":{"amount":950,"customer_age_days":400,"prior_invoices":12,"late_ratio":0.2,"weekday":2,"month":9}}' http://localhost:8088/invoices/predict
   ```

   You can also call `/predict` directly as a shorthand alias for `/invoices/predict`:

   ```bash
   curl -H "X-API-Key: $AI_API_KEY" -H "Content-Type: application/json" -d '{"features":{"amount":950,"customer_age_days":400,"prior_invoices":12,"late_ratio":0.2,"weekday":2,"month":9}}' http://localhost:8088/predict
   ```

5. (Optional) Interact with the classifier management endpoints:

   ```bash
   curl -H "X-API-Key: $AI_API_KEY" http://localhost:8088/models/classifier/status
   curl -H "X-API-Key: $AI_API_KEY" -F "file=@data/training/classifier_example.csv" http://localhost:8088/models/classifier/train
   curl -H "X-API-Key: $AI_API_KEY" -H "Content-Type: application/json" -d '{"text":"POS RECEIPT Store 123 Total 11.82"}' http://localhost:8088/models/classifier/classify
   ```

### Configuration

The API reads configuration from environment variables (or a `.env` file). Key knobs include:

| Variable                | Default   | Description                                                                 |
| ----------------------- | --------- | --------------------------------------------------------------------------- |
| `AI_API_KEY`            | *unset*   | Shared secret required in the `X-API-Key` header for all non-health routes. |
| `MAX_UPLOAD_BYTES`      | `5242880` | Maximum allowed size for uploaded files (default: 5 MiB).                   |
| `MAX_TEXT_LENGTH`       | `20000`   | Maximum characters accepted for classification endpoints.                   |
| `MAX_FEATURE_FIELDS`    | `50`      | Maximum number of keys accepted in predictive feature payloads.             |
| `MAX_JSON_BODY_BYTES`   | *unset*   | Optional upper bound (bytes) for JSON feature payloads.                     |
| `RATE_LIMIT_PER_MINUTE` | *unset*   | Reserved for future throttling/telemetry integrations.                      |

Set these before starting the server (via `.env` or environment variables) to tune request validation and security.

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

The API project wires an `HttpClient` with retries, timeouts, and API-key propagation:

```csharp
builder.Services
    .AddHttpClient<AIClient>(client =>
    {
        client.BaseAddress = new Uri("http://127.0.0.1:8088");
        client.Timeout = TimeSpan.FromSeconds(20);
        var apiKey = Environment.GetEnvironmentVariable("AI_API_KEY") ?? string.Empty;
        if (!string.IsNullOrWhiteSpace(apiKey))
        {
            client.DefaultRequestHeaders.Add("X-API-Key", apiKey);
        }
    })
    .AddPolicyHandler(RetryPolicy());
```

Use `AIClient` in your controllers or background services once registered.

### Operations helpers

* `scripts/generate_synthetic.py` — generates synthetic classifier + predictive training CSVs.
* `scripts/generate_predictive_synth.py` — quickly builds payment prediction CSVs.
* `scripts/watchdog.ps1` — simple Windows watchdog that restarts the packaged API if the `/health` endpoint stops responding.

## Next steps

* Enhance OCR with layout-aware parsing.
* Expand NLP rules and add locale-aware total extraction.
* Broaden the dataset and labels for the classifier and predictive models.
* Add retries, telemetry, and circuit breakers on the .NET side.
