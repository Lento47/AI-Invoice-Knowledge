#!/usr/bin/env python3
"""CLI tool for generating signed license artifacts."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from ai_invoice.license import canonicalize_payload, encode_license_token


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_datetime(value: str, *, field: str, end_of_day: bool = False) -> datetime:
    normalized = value.strip()
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{field} must be an ISO-8601 timestamp or YYYY-MM-DD.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    if end_of_day and normalized.count(":") == 0:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed


def _parse_metadata(entries: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise argparse.ArgumentTypeError("Metadata entries must be KEY=VALUE.")
        key, value = entry.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError("Metadata keys must be non-empty.")
        metadata[key] = value.strip()
    return metadata


def _clean_features(features: list[str]) -> list[str]:
    cleaned: list[str] = []
    for feature in features:
        name = feature.strip()
        if not name:
            continue
        if name not in cleaned:
            cleaned.append(name)
    return cleaned


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate signed license artifacts for tenants.")
    parser.add_argument("--private-key", type=Path, required=True, help="Path to the PEM-encoded Ed25519 private key.")
    parser.add_argument(
        "--password-file",
        type=Path,
        help="Optional file containing the passphrase for the encrypted private key.",
    )
    parser.add_argument("--tenant-id", required=True, help="Unique tenant identifier embedded in the license.")
    parser.add_argument("--tenant-name", help="Human-friendly tenant label to embed in the license payload.")
    parser.add_argument(
        "--meta",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Additional tenant metadata (repeatable).",
    )
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        help="Feature flag to enable for this tenant (repeatable).",
    )
    parser.add_argument(
        "--expires",
        required=True,
        help="Expiration timestamp (ISO-8601). Dates are treated as end-of-day UTC.",
    )
    parser.add_argument(
        "--issued-at",
        help="Override the issuance timestamp (defaults to the current UTC time).",
    )
    parser.add_argument("--device", help="Optional device binding identifier.")
    parser.add_argument("--key-id", help="Identifier for the signing key (useful during rotation).")
    parser.add_argument("--token-only", action="store_true", help="Emit only the base64 token to stdout.")
    parser.add_argument("--output", type=Path, help="File to write the license artifact JSON (defaults to stdout only).")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output for readability.")
    return parser.parse_args()


def _sign_payload(private_key: Path, payload: bytes, password_file: Path | None) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as payload_file:
        payload_file.write(payload)
        payload_path = Path(payload_file.name)
    signature_path = Path(tempfile.NamedTemporaryFile(delete=False).name)

    cmd = [
        "openssl",
        "pkeyutl",
        "-sign",
        "-inkey",
        str(private_key),
        "-rawin",
        "-in",
        str(payload_path),
        "-out",
        str(signature_path),
    ]
    if password_file is not None:
        cmd.extend(["-passin", f"file:{password_file}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        payload_path.unlink(missing_ok=True)
        signature_path.unlink(missing_ok=True)
        raise SystemExit("OpenSSL executable is required to sign licenses.") from exc

    payload_path.unlink(missing_ok=True)
    if result.returncode != 0:
        signature_path.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "").strip()
        message = f"License signing failed via OpenSSL ({detail})." if detail else "License signing failed via OpenSSL."
        raise SystemExit(message)

    signature = signature_path.read_bytes()
    signature_path.unlink(missing_ok=True)
    return signature


def build_payload(args: argparse.Namespace, *, issued_at: datetime, expires_at: datetime) -> dict[str, Any]:
    tenant: dict[str, Any] = {"id": args.tenant_id}
    if args.tenant_name:
        tenant["name"] = args.tenant_name
    metadata = _parse_metadata(args.meta)
    if metadata:
        tenant["metadata"] = metadata

    payload: dict[str, Any] = {
        "tenant": tenant,
        "features": _clean_features(args.feature),
        "issued_at": _isoformat(issued_at),
        "expires_at": _isoformat(expires_at),
        "token_id": str(uuid.uuid4()),
    }
    if args.device:
        payload["device"] = args.device.strip()
    if args.key_id:
        payload["key_id"] = args.key_id.strip()
    return payload


def main() -> None:
    args = parse_args()

    issued_at = _parse_datetime(args.issued_at, field="--issued-at") if args.issued_at else datetime.now(timezone.utc)
    expires_at = _parse_datetime(args.expires, field="--expires", end_of_day=True)
    if expires_at <= issued_at:
        raise SystemExit("Expiration must be after the issuance timestamp.")

    if not args.private_key.exists():
        raise SystemExit(f"Private key not found: {args.private_key}")
    if args.password_file and not args.password_file.exists():
        raise SystemExit(f"Password file not found: {args.password_file}")

    payload = build_payload(args, issued_at=issued_at, expires_at=expires_at)
    payload_bytes = canonicalize_payload(payload)
    signature = _sign_payload(args.private_key, payload_bytes, args.password_file)
    artifact = {
        "version": 1,
        "algorithm": "ed25519",
        "payload": payload,
        "signature": base64.urlsafe_b64encode(signature).decode("utf-8"),
    }

    token = encode_license_token(artifact)
    output_data: Any
    if args.token_only:
        output_data = token
    else:
        output_data = {"artifact": artifact, "token": token}

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.pretty:
            artifact_text = json.dumps(artifact, indent=2, sort_keys=True)
        else:
            artifact_text = json.dumps(artifact, separators=(",", ":"), sort_keys=True)
        args.output.write_text(artifact_text + "\n", encoding="utf-8")
        print(f"Wrote license artifact to {args.output}", file=sys.stderr)

    if args.token_only:
        print(token)
    else:
        if args.pretty:
            print(json.dumps(output_data, indent=2))
        else:
            print(json.dumps(output_data, separators=(",", ":")))


if __name__ == "__main__":
    main()

