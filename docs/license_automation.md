# License automation playbook

This guide documents an internal workflow for triaging license requests, issuing
signed tokens for approved tenants, and tracking the lifecycle of each
subscription tier. The automation centers on the `scripts/license_workflow.py`
helper, which orchestrates approvals and calls the existing signing pipeline.

## 1. Prerequisites

1. Generate the Ed25519 keypair on a secure workstation. The private key
   (`license_private.pem`) stays in your vault; only the public verifier
   (`license_public.pem`) is deployed with the API service.
2. Install OpenSSL on the workstation where approvals are processed. The helper
   invokes `openssl pkeyutl` to sign payloads with the private key.
3. (Optional) Use `scripts/security_provision.py` to create the keypair and API
   secrets in a repeatable way (see below).
4. Decide where to persist the workflow ledger. By default the script stores
   data in `data/license_requests.json`, but you can point to another location
   with `--store` (for example, a shared network drive).

## 2. Define subscription tiers

The workflow ships with the following tiers out of the box:

| Tier       | Duration |
|------------|----------|
| `monthly`  | 1 month  |
| `quarterly`| 3 months |
| `semester` | 6 months |
| `annual`   | 12 months|
| `biennial` | 24 months|

For multi-year or bespoke deals, supply `--duration-months` when recording the
request (for example, `--tier custom --duration-months 36`). The override is
stored with the request and used during approval.

## 2a. Provisioning helpers

### Use the packaged `invoiceai` CLI (preferred)

Installing the project in editable mode (`pip install -e .`) exposes a new
`invoiceai` console command that wraps key lifecycle actions:

```bash
# Generate an Ed25519 license keypair (prompts before overwriting files)
invoiceai generate license key --output-dir keys

# Create matching API and admin secrets in JSON form
invoiceai generate apikey --format json --pretty

# Copy a public verifier into place and record the path in data/settings.json
invoiceai install license ./keys/license_public.pem --destination /opt/ai-invoice/keys/license_public.pem

# Persist the API key (and reuse it for the admin console) in the settings store
invoiceai install api "$(openssl rand -hex 32)" --apply-to-admin

# Verify a signed license token against the configured public key
invoiceai validate license "$(cat /secure/tenant_license.token)" --json
```

`install` commands mutate `data/settings.json` via the internal settings store,
so the backend sees the new secrets immediately without editing JSON by hand.
Only public verification material is ever written; keep `license_private.pem`
offline in your vault.

### Legacy Python helper

The `scripts/security_provision.py` utility bundles the same setup tasks so you
can generate signing keys, API secrets, and environment snippets without
copying commands by hand.

### Generate a fresh Ed25519 keypair

```
python scripts/security_provision.py generate-keypair \
  --output-dir keys \
  --private-name license_private.pem \
  --public-name license_public.pem
```

- Add `--password-file path/to/passphrase.txt` (or `--password secret`) to
  encrypt the private key.
- Use `--force` if you intentionally want to overwrite existing files.

### Produce API and admin secrets

```
python scripts/security_provision.py generate-api-keys --length 64 --format env
```

This prints both `AI_API_KEY` and `ADMIN_API_KEY`. Provide `--output .env` to
persist them, or `--format json` for machine-readable tooling.

### Render deployment snippets

Create environment exports for shells or CI pipelines:

```
python scripts/security_provision.py render-env \
  --api-key <AI_API_KEY> \
  --admin-key <ADMIN_API_KEY> \
  --public-key-path /opt/ai-invoice/keys/license_public.pem \
  --format bash
```

For systemd drop-ins:

```
python scripts/security_provision.py systemd-override \
  --api-key <AI_API_KEY> \
  --admin-key <ADMIN_API_KEY> \
  --public-key-path /opt/ai-invoice/keys/license_public.pem \
  --service ai-invoice.service \
  --output /tmp/override.conf
```

If you maintain the public key inline instead of on disk, replace
`--public-key-path` with `--public-key-inline /path/to/license_public.pem` or
paste the PEM directly after the flag.

## 3. Capture incoming requests

Record each prospect with the `request` subcommand. You can associate metadata,
feature flags, and free-form notes to inform the review process.

```bash
./scripts/license_workflow.py request \
  --tenant-id acme-co \
  --tenant-name "Acme Co" \
  --tier quarterly \
  --feature advanced_reports \
  --meta plan=premium \
  --notes "Bundle with onboarding credit"
```

For longer contracts:

```bash
./scripts/license_workflow.py request \
  --tenant-id contoso-enterprise \
  --tenant-name "Contoso Enterprise" \
  --tier custom \
  --duration-months 36 \
  --meta segment=enterprise \
  --notes "Three-year pilot with option to extend"
```

Each request is assigned a UUID and stored with status `pending` until a
decision is recorded.

## 4. Review queue and drill into details

List and filter the queue:

```bash
./scripts/license_workflow.py list              # show all requests
./scripts/license_workflow.py list --status pending
```

Inspect an individual record:

```bash
./scripts/license_workflow.py show 1f5a0b72-...
```

## 5. Approve and issue licenses

When a request is approved, the helper signs a payload with your private key and
stores both the JSON artifact and the encoded token alongside the audit trail.

```bash
./scripts/license_workflow.py approve 1f5a0b72-... \
  --private-key /secure/vault/license_private.pem \
  --decision-by "Lejzer T." \
  --start 2025-01-01 \
  --issued-at 2024-12-15T12:00:00Z
```

If the private key is encrypted, also pass `--password-file /path/to/passphrase`.
The script calculates the expiration using the tier duration (or the custom
override), signs the payload, and stores the resulting token in the ledger. The
console output summarizes the expiration date so you can communicate it back to
the customer.

## 6. Deny requests

For prospects that do not meet approval criteria, record a denial with an audit
note:

```bash
./scripts/license_workflow.py deny 1f5a0b72-... \
  --reason "Insufficient verification" \
  --decision-by "Compliance Bot"
```

Denied entries remain in the ledger for historical traceability.

## 7. Exporting and rotating

- The ledger is JSON; you can sync it to your CRM or BI tooling by parsing the
  file and joining against billing records.
- For rotation events, re-run `approve` with a new request to emit a fresh
  license token, then add the previous token’s `token_id` to the revoke list in
  the admin console.

## 8. TLS and deployment reminders

This workflow covers license issuance only. Continue to manage API keys via your
secrets pipeline, stage the public verifier on application hosts, and terminate
TLS at the load balancer or reverse proxy layer.
