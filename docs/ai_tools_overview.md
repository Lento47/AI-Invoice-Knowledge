# Using the AI tools

This guide summarises the touch points that ship with the project so operators can
quickly exercise the extraction, classification, prediction, and agent-driven
workflows.

## 1. Call the REST API directly

The FastAPI service exposes the core AI capabilities via JSON and multipart
endpoints. Start the server (see the README for full setup instructions) and
include both authentication headers when they are enabled:

- `X-API-Key` – shared secret configured through the `AI_API_KEY`/`API_KEY`
  environment variables.
- `X-License` – signed license token that carries feature flags such as
  `extract`, `classify`, and `predict`.

Example session against a local server on port 8088:

```bash
curl http://localhost:8088/health/

curl -H "X-API-Key: $AI_API_KEY" \
     -H "X-License: $AI_LICENSE" \
     -F "file=@data/samples/invoice1.pdf" \
     http://localhost:8088/invoices/extract

curl -H "X-API-Key: $AI_API_KEY" \
     -H "X-License: $AI_LICENSE" \
     -H "Content-Type: application/json" \
     -d '{"text":"ACME INVOICE #F-1002 ..."}' \
     http://localhost:8088/invoices/classify

curl -H "X-API-Key: $AI_API_KEY" \
     -H "X-License: $AI_LICENSE" \
     -H "Content-Type: application/json" \
     -d '{"features":{"amount":950,"customer_age_days":400,"prior_invoices":12,"late_ratio":0.2,"weekday":2,"month":9}}' \
     http://localhost:8088/invoices/predict
```

## 2. Use the web portal

Navigate to [http://localhost:8088/portal](http://localhost:8088/portal) while
the API is running. The portal mirrors the REST endpoints, storing credentials
in the browser only when you opt in. It provides:

- drag-and-drop invoice extraction with inline validation feedback,
- a text area for classification experiments,
- a feature table for payment prediction requests,
- optional customs/TICA PDF export when the module is bundled.

For a detailed walkthrough (including licensing, feature flags, and
troubleshooting tips) see [`docs/invoice_portal.md`](invoice_portal.md).

## 3. Automate from Python with the deep agent helper

The `ai_invoice.agents` package wires LangGraph deep agents to the invoice tool
suite. Install the optional dependency and instantiate the helper:

```bash
pip install deepagents
```

```python
from ai_invoice.agents import create_invoice_deep_agent

agent = create_invoice_deep_agent()
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Summarise invoice1.txt and predict when it will be paid.",
            }
        ],
        "files": {
            "invoice1.txt": open("data/samples/invoice1.txt", "r", encoding="utf-8").read(),
        },
    }
)
print(result["messages"][-1]["content"])
```

The factory exposes the OCR parser, classifier, and payment prediction tools by
default. Pass `extra_tools=` or `instructions=` to customise behaviour. Refer to
[`docs/deep_agents.md`](deep_agents.md) for configuration details.

## 4. Integrate with the .NET client

The `dotnet/AIInvoiceSystem.Core` project ships an `AIClient` wrapper around the
REST API. After restoring the solution:

```powershell
cd dotnet
dotnet restore
```

Register the client with dependency injection and supply the API key via
configuration or environment variables. The helper handles retries, timeouts,
and header propagation, so downstream code can call methods like
`ExtractInvoiceAsync`, `ClassifyTextAsync`, and `PredictAsync` without manually
composing HTTP requests. See [`docs/operations.md`](operations.md) for guidance
on configuring the HTTP client resilience settings.

## 5. Reuse the workspace data hooks (frontend)

The React workspace under `apps/ui/` includes hooks that call the same backend
endpoints once credentials are captured in the *Authentication* card. These
hooks expose loading, error, and optimistic states, making it straightforward to
build new UI surfaces that lean on the AI features without re-implementing
request plumbing. Review `apps/ui/src/hooks/useWorkspaceData.ts` for examples of
how to subscribe to invoice analytics, detail views, vendor listings, reports,
and approval actions.

Together these entry points let analysts, developers, and operators exercise the
AI tooling from the command line, web, desktop, and automated agent workflows.
