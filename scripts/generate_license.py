#!/usr/bin/env python3
"""CLI tool for generating signed license artifacts."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from ai_invoice.license_generator import generate_license_artifact


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
        "--certificate-name",
        help="Optional friendly name recorded alongside the license for tracking.",
    )
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
        "issued_at": issued_at,
        "expires_at": expires_at,
        "token_id": str(uuid.uuid4()),
    }
    if args.certificate_name:
        payload["certificate"] = {"name": args.certificate_name.strip()}
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
    artifact, token = generate_license_artifact(
        private_key=args.private_key,
        password_file=args.password_file,
        tenant=payload["tenant"],
        features=payload.get("features", []),
        issued_at=payload["issued_at"],
        expires_at=payload["expires_at"],
        device=payload.get("device"),
        key_id=payload.get("key_id"),
        token_id=payload["token_id"],
        certificate=payload.get("certificate"),
    )

    # generate_license_artifact returns only the tenant payload; reapply any
    # metadata that is not part of the canonical payload structure
    artifact["payload"].update(
        {
            "features": payload.get("features", []),
            "tenant": payload["tenant"],
        }
    )
    if "certificate" in payload:
        artifact["payload"]["certificate"] = payload["certificate"]
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

