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
   ```

5. (Optional) Interact with the classifier management endpoints:

   ```bash
   curl http://localhost:8088/models/classifier/status
   curl -F "file=@data/training/classifier_example.csv" http://localhost:8088/models/classifier/train
   curl -H "Content-Type: application/json" -d '{"text":"POS RECEIPT Store 123 Total 11.82"}' http://localhost:8088/models/classifier/classify
   ```

## Synthetic data generator

Use the synthetic generator to fabricate reproducible training corpora without exposing production data. It relies on
the [`faker`](https://faker.readthedocs.io/) library and deterministic seeds so batches can be regenerated on demand.

```bash
# Generate 500 invoices worth of training data with 60% invoices vs. 40% receipts.
python scripts/generate_synthetic.py --records 500 --class-balance 0.6 --noise 0.25 --seed 1337
```

The command writes four CSV files into `data/training/` with a timestamped suffix:

* `*_classifier_*.csv` – document text/label pairs for the classifier.
* `*_predictive_*.csv` – structured features plus `actual_payment_days` for the predictive model.
* `*_invoices_*.csv` – headline invoice metadata including payment outcomes.
* `*_line_items_*.csv` – exploded invoice line-item details.

### Refreshing the models with synthetic data

1. Regenerate datasets with the CLI above whenever you need a fresh batch. Adjust `--records`, `--class-balance`, and
   `--noise` to influence the corpus size, invoice/receipt ratio, and amount of textual/price jitter.
2. Retrain the classifier by uploading the new classifier CSV to the FastAPI endpoint:

   ```bash
   latest_classifier=$(ls -t data/training/*_classifier_*.csv | head -n 1)
   curl -F "file=@${latest_classifier}" http://localhost:8088/models/classifier/train
   ```

3. Refresh the predictive regression model from the newest predictive CSV:

   ```bash
   latest_predictive=$(ls -t data/training/*_predictive_*.csv | head -n 1)
   uv run python - <<'PY'
   from pathlib import Path
   from ai_invoice.predictive import model

   path = Path("${latest_predictive}")
   metrics = model.train_from_csv_bytes(path.read_bytes())
   print(metrics)
   PY
   ```

The invoice and line item exports are optional references you can use for analytics notebooks or to seed downstream
pipelines.

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
