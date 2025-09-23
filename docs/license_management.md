# License issuance and lifecycle management

This service validates every request against an Ed25519-signed license token. The
private signing key must **never** ship with the application. Store it in an
offline vault or hardware token and distribute only the public key file that the
API uses to verify tokens.

## Key pair generation

1. Run the following on an air-gapped or otherwise trusted workstation:

   ```bash
   openssl genpkey -algorithm ed25519 -out license_private.pem
   openssl pkey -in license_private.pem -pubout -out license_public.pem
   ```

2. Upload `license_private.pem` to your secrets manager (HSM, Vault, encrypted
   removable media, etc.) and remove the plaintext copy.
3. Commit or deploy `license_public.pem` to the API hosts. The repository
   defaults to `keys/license_public.pem`; override the location by setting
   `LICENSE_PUBLIC_KEY_PATH` in the API environment.

## Issuing licenses

Use `scripts/generate_license.py` to mint license artifacts. The CLI shells out
to `openssl`, so ensure it is available on your PATH. The tool accepts tenant
metadata, feature flags, expirations, and optional device bindings.

```bash
uv run python scripts/generate_license.py \
  --private-key /secure/offline/license_private.pem \
  --tenant-id tenant-123 \
  --tenant-name "Acme Robotics" \
  --meta contact_email=ops@acme.test \
  --feature ocr --feature predictive --feature ap \
  --expires 2025-12-31 \
  --device ai-terminal-042 \
  --key-id 2024-q3
```

The command writes a JSON object to stdout containing the license artifact and
the transport token (base64-encoded JSON). Optionally pass `--output` to persist
the artifact, `--pretty` for human-friendly formatting, or `--token-only` when
you only need the header-safe token.

Best practices:

- Keep an issuance log that records the `token_id`, tenant metadata, and
  expiration for auditing.
- Share the raw artifact (`--output`) with the customer so they can retain it as
  proof of entitlement.
- Inject the token into client requests via the `X-License` header.

## Rotation

1. Generate a fresh key pair using the steps above and stage the new public key
   on all API hosts.
2. Reconfigure the API by replacing `keys/license_public.pem` (or updating
   `LICENSE_PUBLIC_KEY_PATH`).
3. Mint new licenses using the same CLI but include a new `--key-id` (for
   example `--key-id 2025-q1`).
4. Distribute updated tokens to tenants and coordinate a cutover window.
5. Once the new tokens are in use, revoke the old private key and remove it from
   your vault.

Caching note: the FastAPI layer caches public keys in-memory. Restart the API or
call `api.security.reset_license_verifier_cache()` after swapping the public key
file to pick up the new material.

## Revocation

Because tokens are self-contained, the primary revocation mechanisms are:

1. **Key rotation** – replacing the public/private pair invalidates every token
   signed by the previous key.
2. **Short expirations** – issue licenses with limited lifetimes (for example 30
   days) and reissue only for tenants in good standing.
3. **Operational deny list** – track the `token_id` column from the issuance log
   and block specific customers at the edge proxy or API gateway if needed.

Document the reason for every revoked token and communicate the action to the
tenant’s point of contact.

