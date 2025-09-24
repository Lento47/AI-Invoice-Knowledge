# Invoice Operations Portal

The invoice portal is a FastAPI-powered workspace that bundles the most common invoice operations into a single, client-side experience. It lives alongside the existing admin console and is ideal for manual testing, demos, and troubleshooting.

## Launching the portal

1. Configure and run the API service as described in the project README. In development you can launch the server with:

   ```bash
   uv run uvicorn api.main:app --reload --port 8088
   ```

2. Navigate to [http://localhost:8088/portal](http://localhost:8088/portal) in a modern browser.

   The UI is entirely client-side and communicates with the FastAPI endpoints that already power automated workflows.

## Authentication and licensing

The portal uses the same security middleware as the REST API:

- **X-API-Key** – required on every non-health request when `API_KEY` (or `AI_API_KEY`) is configured. Enter the key in the *Authentication* card. You can optionally store the value in `localStorage` by ticking **“Remember these secrets on this device”**.
- **X-License-Token** – required when license enforcement is enabled. Paste a signed token containing the necessary feature flags. The UI never persists the token unless you opt in.

If you do not enable the “remember” toggle the secrets stay in memory for the duration of the tab only. Clearing the toggle immediately wipes any stored values.

### Feature flags

Each invoice workflow requires a dedicated feature flag to be present in the license token:

| Feature flag | Enables |
| --- | --- |
| `extract` | Uploading files to `/invoices/extract` for OCR + field parsing. |
| `classify` | Sending text payloads to `/invoices/classify`. |
| `predict` | Scoring feature vectors via `/invoices/predict` or `/predict`. |

If the token is missing a feature you will receive an HTTP 403 with an explanatory message. HTTP 401 responses usually indicate a missing or invalid API key or license signature.

## Available workflows

### Invoice extraction

- Drag-and-drop a PDF, PNG, or JPEG into the drop zone (or browse for a file).
- Click **Extract invoice** to call `POST /invoices/extract`.
- Successful responses show normalized header fields, totals, line items, and the captured raw text. Validation errors (empty file, max upload bytes) surface inline with a red banner.

### Text classification

- Paste unstructured invoice text into the editor and submit the form.
- The UI issues `POST /invoices/classify` and displays the predicted label alongside the probability score.
- Exceeding the configured length limit or submitting empty text returns a 400/413 response that is rendered in the results panel.

### Payment prediction

- Use the feature table to define key/value pairs for predictive scoring. Add or remove rows as needed; blank rows are ignored.
- Select either the canonical `/invoices/predict` endpoint or the `/predict` alias.
- The payload is POSTed as JSON (`{"features": {...}}`). The portal automatically coerces numeric and boolean literals when possible and prints the resulting prediction, risk score, and confidence.

## Troubleshooting

- **413 Payload Too Large** – Increase `MAX_UPLOAD_BYTES` (files) or `MAX_JSON_BODY_BYTES`/`MAX_TEXT_LENGTH` (JSON/text) in your configuration, or submit smaller inputs.
- **401/403 Unauthorized** – Confirm the API key and license token match the service configuration. Token claims must include the required feature flag(s).
- **429 Too Many Requests** – The middleware enforces rate limiting when configured. Reduce request frequency or adjust `RATE_LIMIT_PER_MINUTE`/`RATE_LIMIT_BURST`.
- **Unexpected errors** – Network failures and JSON parsing issues are surfaced inline. Use browser developer tools for deeper inspection and review server logs for stack traces.

The portal enhances (but does not replace) automated integration tests. It is designed to be safe to host in trusted environments where direct API access is appropriate.
