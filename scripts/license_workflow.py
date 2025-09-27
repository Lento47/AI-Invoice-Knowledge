#!/usr/bin/env python3
"""Workflow automation helper for managing tenant license approvals."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from calendar import monthrange
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from ai_invoice.license_generator import generate_license_artifact

DEFAULT_STORE = PROJECT_ROOT / "data" / "license_requests.json"

TIER_MONTHS = {
    "monthly": 1,
    "quarterly": 3,
    "semester": 6,
    "annual": 12,
    "biennial": 24,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def add_months(start: datetime, months: int) -> datetime:
    year = start.year
    month = start.month + months
    day = start.day

    while month > 12:
        month -= 12
        year += 1
    while month <= 0:
        month += 12
        year -= 1

    # Clamp day to end of target month
    _, last_day = monthrange(year, month)
    day = min(day, last_day)

    return start.replace(year=year, month=month, day=day)


@dataclass
class LicenseRequest:
    id: str
    tenant_id: str
    tier: str
    status: str
    submitted_at: str
    metadata: dict[str, str]
    features: list[str]
    tenant_name: str | None = None
    certificate_name: str | None = None
    notes: str | None = None
    custom_months: int | None = None
    issued_at: str | None = None
    expires_at: str | None = None
    decision_at: str | None = None
    decision_by: str | None = None
    license_token: str | None = None
    license_artifact: dict[str, Any] | None = None
    denial_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_store(path: Path) -> list[LicenseRequest]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    requests = []
    for entry in data.get("requests", []):
        requests.append(LicenseRequest(**entry))
    return requests


def save_store(path: Path, requests: list[LicenseRequest]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = {"requests": [req.to_dict() for req in requests]}
    path.write_text(json.dumps(serialized, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_metadata(entries: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise SystemExit("Metadata entries must be KEY=VALUE.")
        key, value = entry.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit("Metadata keys must be non-empty.")
        metadata[key] = value.strip()
    return metadata


def clean_features(features: list[str]) -> list[str]:
    cleaned: list[str] = []
    for feature in features:
        name = feature.strip()
        if not name:
            continue
        if name not in cleaned:
            cleaned.append(name)
    return cleaned


def find_request(requests: list[LicenseRequest], request_id: str) -> LicenseRequest:
    for req in requests:
        if req.id == request_id:
            return req
    raise SystemExit(f"Request {request_id} was not found.")


def cmd_request(args: argparse.Namespace) -> None:
    store = load_store(args.store)
    if args.duration_months is not None and args.duration_months <= 0:
        raise SystemExit("--duration-months must be a positive integer.")
    if args.tier == "custom" and args.duration_months is None:
        raise SystemExit("Custom tiers require --duration-months.")

    request = LicenseRequest(
        id=str(uuid.uuid4()),
        tenant_id=args.tenant_id,
        tier=args.tier,
        status="pending",
        submitted_at=isoformat(utc_now()),
        metadata=parse_metadata(args.meta),
        features=clean_features(args.feature),
        tenant_name=args.tenant_name,
        certificate_name=args.certificate_name,
        notes=args.notes,
        custom_months=args.duration_months,
    )
    store.append(request)
    save_store(args.store, store)
    print(f"Created request {request.id} for tenant {args.tenant_id} ({args.tier}).")


def cmd_list(args: argparse.Namespace) -> None:
    store = load_store(args.store)
    for req in store:
        if args.status and req.status != args.status:
            continue
        label = req.certificate_name or req.tenant_name or "-"
        print(
            f"{req.id} | {req.tenant_id:<20} | {label:<20} | {req.tier:<9} | {req.status:<9} |"
            f" submitted {req.submitted_at}"
        )


def cmd_show(args: argparse.Namespace) -> None:
    store = load_store(args.store)
    req = find_request(store, args.request_id)
    print(json.dumps(req.to_dict(), indent=2, sort_keys=True))


def resolve_months(req: LicenseRequest) -> int:
    if req.custom_months:
        return req.custom_months
    if req.tier not in TIER_MONTHS:
        raise SystemExit(
            f"Unknown tier '{req.tier}'. Provide --duration-months when requesting a custom tier."
        )
    return TIER_MONTHS[req.tier]


def cmd_approve(args: argparse.Namespace) -> None:
    store = load_store(args.store)
    req = find_request(store, args.request_id)
    if req.status != "pending":
        raise SystemExit(f"Request {req.id} is already {req.status}.")

    months = resolve_months(req)
    issued_at = datetime.fromisoformat(args.issued_at.replace("Z", "+00:00")).astimezone(timezone.utc) if args.issued_at else utc_now()
    start_at = (
        datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(timezone.utc)
        if args.start
        else issued_at
    )
    expires_at = add_months(start_at, months)

    private_key = Path(args.private_key)
    if not private_key.exists():
        raise SystemExit(f"Private key not found: {private_key}")
    password_file = Path(args.password_file) if args.password_file else None
    if password_file and not password_file.exists():
        raise SystemExit(f"Password file not found: {password_file}")

    tenant: dict[str, Any] = {"id": req.tenant_id}
    if req.tenant_name:
        tenant["name"] = req.tenant_name
    if req.metadata:
        tenant["metadata"] = req.metadata

    certificate: dict[str, Any] | None = None
    if req.certificate_name:
        certificate = {"name": req.certificate_name}

    artifact, token = generate_license_artifact(
        private_key=private_key,
        password_file=password_file,
        tenant=tenant,
        features=req.features,
        issued_at=issued_at,
        expires_at=expires_at,
        token_id=str(uuid.uuid4()),
        certificate=certificate,
    )

    req.status = "approved"
    req.issued_at = isoformat(issued_at)
    req.expires_at = isoformat(expires_at)
    req.decision_at = isoformat(utc_now())
    req.decision_by = args.decision_by
    req.license_token = token
    req.license_artifact = artifact
    save_store(args.store, store)
    print(f"Approved request {req.id}; license expires {req.expires_at}.")


def cmd_deny(args: argparse.Namespace) -> None:
    store = load_store(args.store)
    req = find_request(store, args.request_id)
    if req.status != "pending":
        raise SystemExit(f"Request {req.id} is already {req.status}.")
    req.status = "denied"
    req.decision_at = isoformat(utc_now())
    req.decision_by = args.decision_by
    req.denial_reason = args.reason
    save_store(args.store, store)
    print(f"Denied request {req.id}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage license approvals for AI-Invoice tenants.")
    parser.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_STORE,
        help=f"Path to the license request store (default: {DEFAULT_STORE}).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_request = subparsers.add_parser("request", help="Submit a new license request.")
    p_request.add_argument("--tenant-id", required=True)
    p_request.add_argument("--tenant-name")
    p_request.add_argument(
        "--certificate-name",
        help="Friendly label recorded with the license artifact (for example, the business legal name).",
    )
    p_request.add_argument(
        "--tier",
        choices=sorted(list(TIER_MONTHS.keys()) + ["custom"]),
        required=True,
        help="Subscription tier label.",
    )
    p_request.add_argument("--feature", action="append", default=[], help="Feature flag (repeatable).")
    p_request.add_argument("--meta", action="append", default=[], metavar="KEY=VALUE")
    p_request.add_argument("--notes")
    p_request.add_argument(
        "--duration-months",
        type=int,
        help="Override duration in months for custom tiers (e.g., multi-year contracts).",
    )
    p_request.set_defaults(func=cmd_request)

    p_list = subparsers.add_parser("list", help="List license requests.")
    p_list.add_argument("--status", choices=["pending", "approved", "denied"])
    p_list.set_defaults(func=cmd_list)

    p_show = subparsers.add_parser("show", help="Show a license request in detail.")
    p_show.add_argument("request_id")
    p_show.set_defaults(func=cmd_show)

    p_approve = subparsers.add_parser("approve", help="Approve a pending request and issue a license.")
    p_approve.add_argument("request_id")
    p_approve.add_argument("--private-key", required=True, type=Path)
    p_approve.add_argument("--password-file", type=Path)
    p_approve.add_argument("--decision-by", help="Approver name or ID.")
    p_approve.add_argument("--issued-at", help="Override issuance timestamp (ISO-8601).")
    p_approve.add_argument("--start", help="Optional service start timestamp (ISO-8601).")
    p_approve.set_defaults(func=cmd_approve)

    p_deny = subparsers.add_parser("deny", help="Deny a pending request.")
    p_deny.add_argument("request_id")
    p_deny.add_argument("--reason", required=True)
    p_deny.add_argument("--decision-by", help="Approver name or ID.")
    p_deny.set_defaults(func=cmd_deny)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.store = args.store.resolve()
    args.func(args)


if __name__ == "__main__":
    main()
