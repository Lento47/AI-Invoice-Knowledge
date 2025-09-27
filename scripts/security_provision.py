#!/usr/bin/env python3
"""Utilities for provisioning AI-Invoice security materials."""

from __future__ import annotations

import argparse
import os
import secrets
import stat
import sys
from pathlib import Path
from typing import Iterable

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "The 'cryptography' package is required. Install project dependencies first (e.g. `pip install -e .`)."
    ) from exc


DEFAULT_PRIVATE_NAME = "license_private.pem"
DEFAULT_PUBLIC_NAME = "license_public.pem"


def _ensure_output_file(path: Path, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_private_key(private_key: ed25519.Ed25519PrivateKey, path: Path, *, password: bytes | None) -> None:
    if password:
        encryption = serialization.BestAvailableEncryption(password)
    else:
        encryption = serialization.NoEncryption()

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    path.write_bytes(pem)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _write_public_key(private_key: ed25519.Ed25519PrivateKey, path: Path) -> None:
    public_key = private_key.public_key()
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    except OSError:
        pass


def cmd_generate_keypair(args: argparse.Namespace) -> None:
    output_dir: Path = args.output_dir
    private_path = output_dir / args.private_name
    public_path = output_dir / args.public_name

    _ensure_output_file(private_path, force=args.force)
    _ensure_output_file(public_path, force=args.force)

    password: bytes | None = None
    if args.password_file:
        password = args.password_file.read_text(encoding="utf-8").rstrip("\n").encode("utf-8")
    elif args.password:
        password = args.password.encode("utf-8")

    private_key = ed25519.Ed25519PrivateKey.generate()
    _write_private_key(private_key, private_path, password=password)
    _write_public_key(private_key, public_path)

    print(f"Generated private key: {private_path}")
    print(f"Generated public key:  {public_path}")
    if password:
        print("Private key encrypted with supplied password.")


def _token_hex(length: int) -> str:
    if length <= 0:
        raise SystemExit("--length must be positive.")
    if length % 2:
        raise SystemExit("--length must be an even value to map to full bytes.")
    return secrets.token_hex(length // 2)


def cmd_generate_api_keys(args: argparse.Namespace) -> None:
    api_key = args.api_key or _token_hex(args.length)
    admin_key = args.admin_key or (api_key if args.reuse_api_key else _token_hex(args.length))

    if args.format == "json":
        import json

        payload = {
            "AI_API_KEY": api_key,
            "ADMIN_API_KEY": admin_key,
        }
        text = json.dumps(payload, indent=2 if args.pretty else None)
    elif args.format == "env":
        lines = [f"AI_API_KEY={api_key}", f"ADMIN_API_KEY={admin_key}"]
        text = "\n".join(lines)
    else:
        text = (
            "AI_API_KEY="
            + api_key
            + ("\nADMIN_API_KEY=" + admin_key if admin_key else "")
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote secrets to {args.output}")
    else:
        print(text)


def _resolve_inline_pem(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = Path(value)
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return value


def _render_env_lines(
    *,
    api_key: str,
    admin_key: str,
    license_key_path: str | None,
    inline_pem: str | None,
    algorithm: str,
    tls_cert_path: str | None,
    tls_key_path: str | None,
) -> list[str]:
    lines = [f"AI_API_KEY={api_key}"]
    lines.append(f"ADMIN_API_KEY={admin_key}")
    lines.append(f"LICENSE_ALGORITHM={algorithm}")
    if license_key_path and inline_pem:
        raise SystemExit("Provide either --public-key-path or --public-key-inline, not both.")
    if license_key_path:
        lines.append(f"LICENSE_PUBLIC_KEY_PATH={license_key_path}")
    elif inline_pem:
        lines.append(f"LICENSE_PUBLIC_KEY={inline_pem}")
    else:
        raise SystemExit("One of --public-key-path or --public-key-inline is required.")
    if (tls_cert_path and not tls_key_path) or (tls_key_path and not tls_cert_path):
        raise SystemExit("TLS configuration requires both --tls-cert-path and --tls-key-path.")
    if tls_cert_path:
        lines.append(f"TLS_CERTFILE_PATH={tls_cert_path}")
        lines.append(f"TLS_KEYFILE_PATH={tls_key_path}")
    return lines


def cmd_render_env(args: argparse.Namespace) -> None:
    algorithm = (args.license_algorithm or "ed25519").strip().upper()
    tls_cert_path = args.tls_cert_path.strip() if args.tls_cert_path else None
    tls_key_path = args.tls_key_path.strip() if args.tls_key_path else None
    lines = _render_env_lines(
        api_key=args.api_key,
        admin_key=args.admin_key or args.api_key,
        license_key_path=args.public_key_path,
        inline_pem=_resolve_inline_pem(args.public_key_inline),
        algorithm=algorithm,
        tls_cert_path=tls_cert_path,
        tls_key_path=tls_key_path,
    )

    if args.format == "bash":
        text = "\n".join(f"export {line}" for line in lines)
    elif args.format == "powershell":
        text = "\n".join(f"$env:{line.replace('=', ' = ')}" for line in lines)
    else:
        text = "\n".join(lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote environment snippet to {args.output}")
    else:
        print(text)


def _render_systemd_block(lines: Iterable[str]) -> str:
    env_lines = [f"Environment={line}" for line in lines]
    block = "[Service]\n" + "\n".join(env_lines)
    return block + "\n"


def cmd_systemd_override(args: argparse.Namespace) -> None:
    algorithm = (args.license_algorithm or "ed25519").strip().upper()
    tls_cert_path = args.tls_cert_path.strip() if args.tls_cert_path else None
    tls_key_path = args.tls_key_path.strip() if args.tls_key_path else None
    env_lines = _render_env_lines(
        api_key=args.api_key,
        admin_key=args.admin_key or args.api_key,
        license_key_path=args.public_key_path,
        inline_pem=_resolve_inline_pem(args.public_key_inline),
        algorithm=algorithm,
        tls_cert_path=tls_cert_path,
        tls_key_path=tls_key_path,
    )

    override_text = _render_systemd_block(env_lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(override_text, encoding="utf-8")
        print(f"Wrote systemd override to {args.output}")
    else:
        print(override_text, end="")

    if args.service:
        unit_dir = Path(f"/etc/systemd/system/{args.service}.d")
        print(
            "\nNext steps:\n"
            f"  sudo mkdir -p {unit_dir}\n"
            f"  sudo tee {unit_dir / 'override.conf'} >/dev/null <<'EOF'\n{override_text}EOF\n"
            "  sudo systemctl daemon-reload\n"
            f"  sudo systemctl restart {args.service}\n"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provision security assets for AI-Invoice deployments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    keypair = subparsers.add_parser("generate-keypair", help="Create an Ed25519 keypair for license signing.")
    keypair.add_argument("--output-dir", type=Path, default=Path("keys"), help="Directory to write the keypair.")
    keypair.add_argument("--private-name", default=DEFAULT_PRIVATE_NAME, help="Filename for the private key.")
    keypair.add_argument("--public-name", default=DEFAULT_PUBLIC_NAME, help="Filename for the public key.")
    keypair.add_argument("--password-file", type=Path, help="File containing password to encrypt the private key.")
    keypair.add_argument("--password", help="Password string to encrypt the private key (use with caution).")
    keypair.add_argument("--force", action="store_true", help="Overwrite existing files if they exist.")
    keypair.set_defaults(func=cmd_generate_keypair)

    secrets_parser = subparsers.add_parser("generate-api-keys", help="Generate API and admin keys.")
    secrets_parser.add_argument("--length", type=int, default=64, help="Length of generated hex tokens (default: 64).")
    secrets_parser.add_argument("--api-key", help="Provide an explicit API key instead of generating one.")
    secrets_parser.add_argument("--admin-key", help="Provide an explicit admin key instead of generating one.")
    secrets_parser.add_argument(
        "--reuse-api-key",
        action="store_true",
        help="Use the API key for admin access when no admin key is supplied.",
    )
    secrets_parser.add_argument(
        "--format",
        choices=("env", "json", "text"),
        default="env",
        help="Output format (default: env).",
    )
    secrets_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    secrets_parser.add_argument("--output", type=Path, help="Write secrets to a file instead of stdout.")
    secrets_parser.set_defaults(func=cmd_generate_api_keys)

    env_parser = subparsers.add_parser("render-env", help="Render environment exports for the service.")
    env_parser.add_argument("--api-key", required=True, help="AI_API_KEY value.")
    env_parser.add_argument("--admin-key", help="ADMIN_API_KEY value (defaults to API key).")
    env_parser.add_argument("--public-key-path", help="Filesystem path to license_public.pem.")
    env_parser.add_argument(
        "--public-key-inline",
        help="Path to a PEM file that should be inlined into LICENSE_PUBLIC_KEY.",
    )
    env_parser.add_argument("--tls-cert-path", help="Path to the TLS certificate (ssl_certfile).")
    env_parser.add_argument("--tls-key-path", help="Path to the TLS private key (ssl_keyfile).")
    env_parser.add_argument(
        "--format",
        choices=("env", "bash", "powershell"),
        default="env",
        help="Output style for the exports (default: env).",
    )
    env_parser.add_argument("--license-algorithm", default="ed25519", help="License algorithm to advertise.")
    env_parser.add_argument("--output", type=Path, help="Write snippet to a file.")
    env_parser.set_defaults(func=cmd_render_env)

    systemd_parser = subparsers.add_parser("systemd-override", help="Generate a systemd override snippet.")
    systemd_parser.add_argument("--api-key", required=True, help="AI_API_KEY value.")
    systemd_parser.add_argument("--admin-key", help="ADMIN_API_KEY value (defaults to API key).")
    systemd_parser.add_argument("--public-key-path", help="Filesystem path to license_public.pem.")
    systemd_parser.add_argument(
        "--public-key-inline",
        help="Path to a PEM file that should be inlined into LICENSE_PUBLIC_KEY.",
    )
    systemd_parser.add_argument("--license-algorithm", default="ed25519", help="License algorithm name.")
    systemd_parser.add_argument("--tls-cert-path", help="Path to the TLS certificate (ssl_certfile).")
    systemd_parser.add_argument("--tls-key-path", help="Path to the TLS private key (ssl_keyfile).")
    systemd_parser.add_argument("--output", type=Path, help="Write override.conf to this path.")
    systemd_parser.add_argument(
        "--service",
        help="Name of the systemd service (used when printing follow-up commands).",
    )
    systemd_parser.set_defaults(func=cmd_systemd_override)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

