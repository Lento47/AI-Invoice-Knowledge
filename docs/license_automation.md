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

#### Generate a turnkey host checklist

`host-playbook` emits copy-ready commands for staging the public verifier,
pinning environment variables, and (optionally) copying TLS materials for your
reverse proxy. Provide the workstation path to your keys, the target location on
the host, and the secure vault destination for the private key. Include
`--api-key` / `--admin-key` to pin specific secrets or omit them to use
`openssl rand` placeholders.

```bash
python scripts/security_provision.py host-playbook \
  --os windows \
  --repo-keys "C:\\Users\\ltrana\\Documents\\aiSystemInvoiceKnowledge\\AI-Invoice-Knowledge-main\\keys" \
  --license-destination "C:\\ai-invoice\\keys\\license_public.pem" \
  --secure-private "\\\\vault-appliance\\dropzone\\licenses\\license_private.pem" \
  --api-key "ab75699b084331b2a011e666a0372efced4d8cfaaeba36b0c1fcf53a19f3932e" \
  --admin-key "577dd6c4c01e035678cb0b18a2bb4709688380501de45d76cea6e4e2044cc971" \
  --service ai-invoice \
  --tls-cert-source "C:\\secure\\tls\\fullchain.pem" \
  --tls-cert-destination "C:\\ai-invoice\\tls\\fullchain.pem" \
  --tls-key-source "C:\\secure\\tls\\privkey.pem" \
  --tls-key-destination "C:\\ai-invoice\\tls\\privkey.pem"
```

For Linux output, switch `--os linux` and point the arguments at the desired
paths. The generated script covers:

1. Creating or refreshing the Ed25519 keypair on your workstation.
2. Moving the private key into your secure store and deleting the working copy.
3. Copying the public verifier into its runtime directory.
4. Pinning `AI_API_KEY`, `ADMIN_API_KEY`, and `LICENSE_PUBLIC_KEY_PATH` via
   systemd or Windows environment variables.
5. (Optional) Copying TLS certificate/key files into a directory for your proxy
   or load balancer.

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

### Stage verification and TLS assets together

Use the `stage-assets` subcommand to copy an existing public verifier into its
runtime location and, optionally, stage HTTPS materials for the proxy layer.
This command never touches the private signing key—it remains your vault’s
responsibility.

```
python scripts/security_provision.py stage-assets \
  --license-public ./keys/license_public.pem \
  --license-destination /opt/ai-invoice/keys/license_public.pem \
  --pin-license-path --systemd-snippet \
  --api-key "$(openssl rand -hex 32)" \
  --admin-key "$(openssl rand -hex 32)" \
  --tls-certificate /secure/tls/fullchain.pem \
  --tls-key /secure/tls/privkey.pem \
  --tls-directory /etc/ssl/ai-invoice
```

The script will:

1. Copy `license_public.pem` into the destination directory (creating it if
   needed) with restrictive permissions.
2. Leave the private Ed25519 key untouched so it can stay in your secrets
   infrastructure.
3. When TLS paths are provided, copy the certificate and private key into the
   supplied directory so your reverse proxy (NGINX, IIS, etc.) can reference
   them.
4. Print optional environment exports and a systemd drop-in snippet that pin
   the new `LICENSE_PUBLIC_KEY_PATH`.

> **Reminder:** The FastAPI service remains HTTP-only. Point your TLS terminator
> at the copied certificate/key pair and forward plain HTTP traffic to the API
> container or service once termination is complete.

### Recommended locations

- **Linux API hosts**
  - License verifier: `/opt/ai-invoice/keys/license_public.pem`
  - TLS assets (for NGINX/HAProxy): `/etc/ssl/ai-invoice/`

- **Windows API hosts**
  - License verifier: `C:\\ai-invoice\\keys\\license_public.pem`
  - TLS assets: Windows certificate store or `C:\\ai-invoice\\tls\\` for
    reverse proxies such as IIS or nginx-windows.

Keep `license_private.pem` in your vault/HSM. If you export a TLS private key to
disk for automation, secure the directory (`icacls`/`chmod 600`) and remove it
after importing the key into your platform tooling.

### Stage the public verifier on application hosts

The running service only needs the public verifier. After generating the
keypair, copy `license_public.pem` onto each API node while keeping the private
key in your secrets vault.

**Windows (PowerShell)**

```
New-Item -ItemType Directory -Path 'C:\ai-invoice\keys' -Force
Copy-Item 'C:\path\to\AI-Invoice-Knowledge\keys\license_public.pem' `
          'C:\ai-invoice\keys\license_public.pem' -Force

[Environment]::SetEnvironmentVariable('LICENSE_PUBLIC_KEY_PATH', 'C:\ai-invoice\keys\license_public.pem', 'Machine')
```

**Linux (systemd)**

```
sudo install -d -m 0750 /opt/ai-invoice/keys
sudo install -m 0640 /secure-transfer/license_public.pem /opt/ai-invoice/keys/license_public.pem

sudo mkdir -p /etc/systemd/system/ai-invoice.service.d
sudo tee /etc/systemd/system/ai-invoice.service.d/override.conf >/dev/null <<'EOF'
[Service]
Environment=LICENSE_PUBLIC_KEY_PATH=/opt/ai-invoice/keys/license_public.pem
Environment=AI_API_KEY=<AI_API_KEY>
Environment=ADMIN_API_KEY=<ADMIN_API_KEY>
EOF

sudo systemctl daemon-reload
sudo systemctl restart ai-invoice.service
```

Replace `<AI_API_KEY>` and `<ADMIN_API_KEY>` with the generated secrets (if you
reuse the API key for admin access, omit `ADMIN_API_KEY`). When running in
containers or ephemeral environments, set `LICENSE_PUBLIC_KEY` to the PEM
string instead of managing a file on disk.

### TLS reminder

HTTPS termination remains the responsibility of your reverse proxy, load
balancer, or platform layer (NGINX, IIS, service mesh, etc.). The application
exposes configuration only for API secrets and the public license verifier; it
does not accept private keys or TLS certificates through the settings surface.

## 3. Capture incoming requests

Record each prospect with the `request` subcommand. You can associate metadata,
feature flags, and free-form notes to inform the review process.

```bash
./scripts/license_workflow.py request \
  --tenant-id acme-co \
  --tenant-name "Acme Co" \
  --certificate-name "Acme Co FY25" \
  --tier quarterly \
  --feature advanced_reports \
  --meta plan=premium \
  --notes "Bundle with onboarding credit"
```

`--certificate-name` lets you stamp a human-readable label onto the signed
artifact (for example the business' legal name, billing cycle, or contract
identifier) so downstream tooling can trace the license without relying solely
on the tenant ID.

For longer contracts:

```bash
./scripts/license_workflow.py request \
  --tenant-id contoso-enterprise \
  --tenant-name "Contoso Enterprise" \
  --certificate-name "Contoso 3-Year" \
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
