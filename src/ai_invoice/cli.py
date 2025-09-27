"""Command-line interface for provisioning AI-Invoice secrets and licenses."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "The 'cryptography' package is required. Install project dependencies first (e.g. `pip install -e .`)."
    ) from exc

from ai_invoice.license import LicenseExpiredError, LicenseVerificationError, LicenseVerifier
from ai_invoice.settings_store import SettingsStore

DEFAULT_PRIVATE_NAME = "license_private.pem"
DEFAULT_PUBLIC_NAME = "license_public.pem"
DEFAULT_KEYS_DIR = Path("keys")


@dataclass(slots=True)
class SettingsMutation:
    """Representation of a settings update operation."""

    description: str
    data: dict[str, Any]


def _store_path() -> SettingsStore:
    return SettingsStore()


def _load_settings() -> dict[str, Any]:
    return _store_path().load()


def _save_settings(payload: dict[str, Any]) -> None:
    _store_path().save(payload)


def _token_hex(length: int) -> str:
    if length <= 0:
        raise SystemExit("--length must be positive.")
    if length % 2:
        raise SystemExit("--length must be an even value to map to full bytes.")
    return secrets.token_hex(length // 2)


def _normalize_destination(path: str | None) -> Path:
    if path is None or path.strip() == "":
        return (Path.cwd() / DEFAULT_KEYS_DIR / DEFAULT_PUBLIC_NAME).resolve()
    return Path(path).expanduser().resolve()


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pem)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_public_key(private_key: ed25519.Ed25519PrivateKey, path: Path) -> None:
    pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pem)
    try:
        os.chmod(path, 0o640)
    except OSError:
        pass


def cmd_generate_license_key(args: argparse.Namespace) -> None:
    private_path = Path(args.output_dir).expanduser() / (args.private_name or DEFAULT_PRIVATE_NAME)
    public_path = Path(args.output_dir).expanduser() / (args.public_name or DEFAULT_PUBLIC_NAME)

    if not args.force:
        for candidate in (private_path, public_path):
            if candidate.exists():
                raise SystemExit(f"Refusing to overwrite existing file: {candidate}")

    password: bytes | None = None
    if args.password_file:
        password = Path(args.password_file).expanduser().read_text(encoding="utf-8").rstrip("\n").encode("utf-8")
    elif args.password:
        password = args.password.encode("utf-8")

    private_key = ed25519.Ed25519PrivateKey.generate()
    _write_private_key(private_key, private_path, password=password)
    _write_public_key(private_key, public_path)

    print(f"Generated private key: {private_path}")
    print(f"Generated public key:  {public_path}")
    if password:
        print("Private key encrypted with supplied password.")


def cmd_generate_api_key(args: argparse.Namespace) -> None:
    api_key = args.api_key or _token_hex(args.length)
    admin_key = args.admin_key or (api_key if args.reuse_api_key else _token_hex(args.length))

    if args.format == "json":
        payload = {"AI_API_KEY": api_key, "ADMIN_API_KEY": admin_key}
        text = json.dumps(payload, indent=2 if args.pretty else None)
    elif args.format == "env":
        lines = [f"AI_API_KEY={api_key}", f"ADMIN_API_KEY={admin_key}"]
        text = "\n".join(lines)
    else:
        text = f"AI_API_KEY={api_key}\nADMIN_API_KEY={admin_key}".strip()

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote secrets to {output_path}")
    else:
        print(text)


def _prepare_settings_mutation(update: dict[str, Any]) -> SettingsMutation:
    stored = _load_settings()
    stored.update(update)
    return SettingsMutation(description="settings", data=stored)


def _apply_mutation(mutation: SettingsMutation) -> None:
    _save_settings(mutation.data)
    print(f"Updated {mutation.description} store at {_store_path().path}.")


def cmd_install_api(args: argparse.Namespace) -> None:
    admin_value = args.admin_key or (args.api_key if args.apply_to_admin else None)
    update: dict[str, Any] = {"api_key": args.api_key}
    if args.allow_anonymous is not None:
        update["allow_anonymous"] = bool(args.allow_anonymous)
    if admin_value:
        update["admin_api_key"] = admin_value
    elif args.clear_admin:
        update["admin_api_key"] = None

    mutation = _prepare_settings_mutation(update)
    _apply_mutation(mutation)
    print("Stored API key in settings store.")
    if admin_value:
        print("Stored admin API key in settings store.")
    elif args.clear_admin:
        print("Cleared admin API key from settings store.")


def _coerce_inline_pem(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = Path(value)
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return value


def cmd_install_license(args: argparse.Namespace) -> None:
    algorithm = (args.algorithm or "ed25519").strip().upper()
    source = Path(args.license).expanduser()

    if args.inline:
        pem_data = _coerce_inline_pem(args.license)
        if pem_data is None:
            raise SystemExit("Inline license data is empty.")
        update = {
            "license_public_key": pem_data.strip(),
            "license_public_key_path": None,
            "license_algorithm": algorithm,
        }
        mutation = _prepare_settings_mutation(update)
        _apply_mutation(mutation)
        print("Stored inline public key in settings store.")
        return

    if source.exists():
        destination = _normalize_destination(args.destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        update = {
            "license_public_key_path": str(destination),
            "license_public_key": None,
            "license_algorithm": algorithm,
        }
        mutation = _prepare_settings_mutation(update)
        _apply_mutation(mutation)
        print(f"Copied license public key to {destination}.")
    else:
        pem_data = args.license.strip()
        if not pem_data:
            raise SystemExit("License value must be a PEM string or path to a PEM file.")
        update = {
            "license_public_key": pem_data,
            "license_public_key_path": None,
            "license_algorithm": algorithm,
        }
        mutation = _prepare_settings_mutation(update)
        _apply_mutation(mutation)
        print("Stored inline public key in settings store.")


def _resolve_verifier(args: argparse.Namespace) -> LicenseVerifier:
    if args.public_key:
        pem_data = _coerce_inline_pem(args.public_key)
        if not pem_data:
            raise SystemExit("--public-key must point to a PEM file or contain PEM text.")
        return LicenseVerifier.from_public_key_string(pem_data)

    if args.public_key_path:
        return LicenseVerifier.from_public_key_path(args.public_key_path)

    stored = _load_settings()
    inline = stored.get("license_public_key")
    path = stored.get("license_public_key_path")
    if inline:
        return LicenseVerifier.from_public_key_string(str(inline))
    if path:
        return LicenseVerifier.from_public_key_path(path)
    raise SystemExit(
        "No license public key configured. Provide --public-key or --public-key-path, or install a key first."
    )


def cmd_validate_license(args: argparse.Namespace) -> None:
    verifier = _resolve_verifier(args)
    token = args.license.strip()
    if not token:
        raise SystemExit("License token must not be empty.")

    try:
        payload = verifier.verify_token(token)
    except LicenseExpiredError as exc:
        raise SystemExit(f"License token has expired: {exc}") from exc
    except LicenseVerificationError as exc:
        raise SystemExit(f"License token is invalid: {exc}") from exc

    print("License token is valid.")
    if args.json:
        print(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        print("Tenant ID:", payload.tenant.id)
        print("Features:", ", ".join(sorted(payload.features)))
        print("Issued at:", payload.issued_at.isoformat())
        print("Expires at:", payload.expires_at.isoformat())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="invoiceai", description="AI-Invoice deployment helper CLI")
    subparsers = parser.add_subparsers(dest="command")

    # generate group
    generate = subparsers.add_parser("generate", help="Generate secrets and key material")
    gen_sub = generate.add_subparsers(dest="generate_command")

    license_parser = gen_sub.add_parser("license", help="Generate an Ed25519 license keypair")
    license_parser.set_defaults(func=cmd_generate_license_key)
    license_parser.add_argument("--output-dir", default=str(DEFAULT_KEYS_DIR), help="Directory to place the keypair")
    license_parser.add_argument("--private-name", help="Filename for the private key (default license_private.pem)")
    license_parser.add_argument("--public-name", help="Filename for the public key (default license_public.pem)")
    license_parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    license_parser.add_argument("--password", help="Encrypt the private key with this password")
    license_parser.add_argument("--password-file", help="Read the private key password from a file")

    license_key_parser = license_parser.add_subparsers(dest="license_sub")
    license_key_alias = license_key_parser.add_parser("key", help=argparse.SUPPRESS)
    license_key_alias.set_defaults(func=cmd_generate_license_key)

    api_parser = gen_sub.add_parser("apikey", aliases=["api-key", "api"], help="Generate API credentials")
    api_parser.set_defaults(func=cmd_generate_api_key)
    api_parser.add_argument("--length", type=int, default=64, help="Total hex length for generated keys (default 64)")
    api_parser.add_argument("--api-key", help="Provide an explicit API key instead of generating one")
    api_parser.add_argument("--admin-key", help="Provide an explicit admin API key")
    api_parser.add_argument("--reuse-api-key", action="store_true", help="Use the same value for admin as API key")
    api_parser.add_argument("--format", choices=["plain", "json", "env"], default="plain", help="Output format")
    api_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    api_parser.add_argument("--output", help="Write results to this file instead of stdout")

    # install group
    install = subparsers.add_parser("install", help="Install secrets into the local settings store")
    install_sub = install.add_subparsers(dest="install_command")

    install_api = install_sub.add_parser("api", help="Persist API credentials to data/settings.json")
    install_api.set_defaults(func=cmd_install_api)
    install_api.add_argument("api_key", help="API key to store in settings")
    install_api.add_argument("--admin-key", help="Optional admin API key to store")
    install_api.add_argument(
        "--apply-to-admin",
        action="store_true",
        help="Reuse the provided API key as the admin key when --admin-key is not supplied",
    )
    install_api.add_argument(
        "--clear-admin",
        action="store_true",
        help="Remove any stored admin API key when --admin-key is omitted",
    )
    install_api.add_argument(
        "--allow-anonymous",
        dest="allow_anonymous",
        action="store_true",
        help="Set allow_anonymous=true in the settings store",
    )
    install_api.add_argument(
        "--no-allow-anonymous",
        dest="allow_anonymous",
        action="store_false",
        help="Set allow_anonymous=false in the settings store",
    )
    install_api.set_defaults(allow_anonymous=None)

    install_license = install_sub.add_parser("license", help="Copy or embed the license public key")
    install_license.set_defaults(func=cmd_install_license)
    install_license.add_argument("license", help="Path to the public key PEM or inline PEM data")
    install_license.add_argument(
        "--destination",
        help="Destination path for the public key file (default keys/license_public.pem)",
    )
    install_license.add_argument(
        "--inline",
        action="store_true",
        help="Treat the provided value as inline PEM even if it looks like a file path",
    )
    install_license.add_argument(
        "--algorithm",
        default="ed25519",
        help="License verification algorithm to record (default ed25519)",
    )

    # validate group
    validate = subparsers.add_parser("validate", help="Validate artifacts against configured keys")
    validate_sub = validate.add_subparsers(dest="validate_command")

    validate_license = validate_sub.add_parser("license", help="Validate a signed license token")
    validate_license.set_defaults(func=cmd_validate_license)
    validate_license.add_argument("license", help="Signed license token to verify")
    validate_license.add_argument("--json", action="store_true", help="Print the validated payload as JSON")
    validate_license.add_argument("--public-key", help="PEM string or file containing the license public key")
    validate_license.add_argument("--public-key-path", help="Path to the license public key")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        args.func(args)
    except KeyboardInterrupt:  # pragma: no cover - user abort
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
