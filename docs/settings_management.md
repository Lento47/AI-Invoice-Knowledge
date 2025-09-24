# Settings management

The FastAPI service now persists configuration to a JSON document instead of relying solely on process
environment variables. This makes it possible to manage authentication keys, request limits, and
CORS configuration without redeploying the service.

## Persistent configuration store

* **Default location:** `data/settings.json`
* **Override path:** set `AI_INVOICE_SETTINGS_PATH=/path/to/settings.json`

The file stores all fields defined in `ai_invoice.config.Settings`. It is safe to edit manually when the
service is offline, but the recommended approach is to use the administrative web UI (described below)
so validation is applied consistently.

The JSON store is loaded during application start. When the file is missing, defaults are applied and the
file is created on first save through the API/UI.

## Environment overrides

Environment variables still work, but they now act as runtime overrides that take precedence over the
JSON store. If an override exists, the admin UI highlights the corresponding field with an
“Environment override” badge. The persisted value is still stored so that removing the environment
variable later will fall back to the saved configuration.

The most common overrides are:

| Variable | Description |
| --- | --- |
| `AI_API_KEY` / `API_KEY` | Primary API token for request authentication. |
| `ADMIN_API_KEY` | Token required by the administrative API/UI. Falls back to `AI_API_KEY` when unset. |
| `ALLOW_ANONYMOUS` | Enable anonymous access to non-health endpoints. |
| `CORS_TRUSTED_ORIGINS` | Comma separated list of origins. Append `|true` to require credentials. |
| `MAX_UPLOAD_BYTES`, `MAX_TEXT_LENGTH`, `MAX_FEATURE_FIELDS` | Request validation knobs. |
| `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_BURST` | Token bucket limiter settings. |

> The service will refuse to start when neither an API key nor `ALLOW_ANONYMOUS=true` is configured.

## Administrative web UI

1. Start the FastAPI application (e.g. `uv run uvicorn api.main:app --reload --port 8088`).
2. Visit `http://localhost:8088/admin` in a browser.
3. Provide the `ADMIN_API_KEY` (or `AI_API_KEY` if the admin key is unset) in the **Admin token** field.
4. Update settings and click **Save changes**.

The UI performs client-side validation and reports when values are currently driven by environment
variables. All changes are persisted to the JSON store and immediately applied to the running
application.

## Migrating from `.env`

1. Ensure your existing `.env` file is loaded (e.g. via `uv run --env-file .env ...`).
2. Start the server and open the admin UI.
3. Authenticate with the current admin token (`ADMIN_API_KEY` if present, otherwise `AI_API_KEY`).
4. Review each section and click **Save changes** to persist the in-memory configuration to
   `data/settings.json`.
5. Remove secrets you no longer want in `.env`. Only keep overrides you intentionally want to lock.

Going forward, routine changes can be performed in the UI. For automated deployments you can still
manage settings by editing the JSON file or by providing environment variable overrides.
