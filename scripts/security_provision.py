#!/usr/bin/env python3
"""Utilities for provisioning AI-Invoice security materials."""

from __future__ import annotations

import argparse
import os
import shutil
import secrets
import stat
import sys
import textwrap
from pathlib import Path, PureWindowsPath
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
    return lines


def cmd_render_env(args: argparse.Namespace) -> None:
    algorithm = (args.license_algorithm or "ed25519").strip().upper()
    lines = _render_env_lines(
        api_key=args.api_key,
        admin_key=args.admin_key or args.api_key,
        license_key_path=args.public_key_path,
        inline_pem=_resolve_inline_pem(args.public_key_inline),
        algorithm=algorithm,
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
    env_lines = _render_env_lines(
        api_key=args.api_key,
        admin_key=args.admin_key or args.api_key,
        license_key_path=args.public_key_path,
        inline_pem=_resolve_inline_pem(args.public_key_inline),
        algorithm=algorithm,
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


def _copy_asset(source: Path, destination: Path, mode: int | None = None) -> Path:
    if not source.is_file():
        raise SystemExit(f"Source file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if mode is not None:
        try:
            os.chmod(destination, mode)
        except OSError:
            pass
    return destination


def cmd_stage_assets(args: argparse.Namespace) -> None:
    license_source = Path(args.license_public).expanduser().resolve()
    license_destination = Path(args.license_destination).expanduser()

    copied_license = _copy_asset(
        license_source,
        license_destination,
        mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP,
    )

    print(f"License public key copied to {copied_license}")
    print("(Private license keys remain in your secure store; this command only stages the public verifier.)")

    tls_cert_path = Path(args.tls_certificate).expanduser() if args.tls_certificate else None
    tls_key_path = Path(args.tls_key).expanduser() if args.tls_key else None
    tls_target_dir = Path(args.tls_directory).expanduser() if args.tls_directory else None

    if any([tls_cert_path, tls_key_path, tls_target_dir]):
        if not (tls_cert_path and tls_key_path and tls_target_dir):
            raise SystemExit(
                "TLS staging requires --tls-certificate, --tls-key, and --tls-directory to be supplied together."
            )

        cert_name = args.tls_certificate_name or tls_cert_path.name
        key_name = args.tls_key_name or tls_key_path.name

        copied_cert = _copy_asset(
            tls_cert_path,
            tls_target_dir / cert_name,
            mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP,
        )
        copied_key = _copy_asset(
            tls_key_path,
            tls_target_dir / key_name,
            mode=stat.S_IRUSR | stat.S_IWUSR,
        )

        print(f"TLS certificate copied to {copied_cert}")
        print(f"TLS private key copied to {copied_key}")
        print(
            "Reminder: configure your reverse proxy or load balancer to reference these TLS assets; the FastAPI service remains HTTP-only."
        )

    env_lines: list[str] = []
    if args.pin_license_path or args.systemd_snippet:
        api_value = args.api_key or "CHANGE_ME_API_KEY"
        admin_value = args.admin_key or (args.api_key if args.api_key else "CHANGE_ME_ADMIN_KEY")
        env_lines = _render_env_lines(
            api_key=api_value,
            admin_key=admin_value,
            license_key_path=str(license_destination),
            inline_pem=None,
            algorithm=(args.license_algorithm or "ed25519").strip().upper(),
        )

    if args.pin_license_path and env_lines:
        print("\nSuggested environment overrides:")
        for line in env_lines:
            print(f"  {line}")

    if args.systemd_snippet and env_lines:
        print("\nSystemd drop-in example (override.conf):\n")
        print(_render_systemd_block(env_lines))


def _ps_quote(path: Path | str) -> str:
    text = str(path)
    return text.replace("'", "''")


def _linux_quote(path: Path | str) -> str:
    text = str(path)
    return text.replace("'", "'\\''")


def _build_windows_playbook(
    *,
    repo_keys: Path,
    license_destination: Path,
    secure_private: Path,
    api_key: str,
    admin_key: str,
    service_name: str | None,
    tls_cert_source: Path | None,
    tls_cert_destination: Path | None,
    tls_key_source: Path | None,
    tls_key_destination: Path | None,
) -> str:
    repo_keys_win = PureWindowsPath(str(repo_keys))
    license_win = PureWindowsPath(str(license_destination))
    secure_win = PureWindowsPath(str(secure_private))

    commands: list[str] = []

    commands.append("# --- Generate the Ed25519 keypair on your workstation ---")
    commands.append(f"Set-Location '{_ps_quote(repo_keys_win)}'")
    commands.append("openssl genpkey -algorithm ed25519 -out license_private.pem")
    commands.append("openssl pkey -in license_private.pem -pubout -out license_public.pem")
    commands.append("")

    commands.append("# --- Archive the private key in your vault and remove the working copy ---")
    commands.append(
        f"Copy-Item 'license_private.pem' '{_ps_quote(secure_win)}' -Force"
    )
    commands.append("Remove-Item 'license_private.pem'")
    commands.append("")

    commands.append("# --- Stage the public verifier on the API host ---")
    commands.append(
        f"New-Item -ItemType Directory -Path '{_ps_quote(license_win.parent)}' -Force"
    )
    commands.append(
        f"Copy-Item '{_ps_quote(repo_keys_win / 'license_public.pem')}' '{_ps_quote(license_win)}' -Force"
    )
    commands.append("")

    commands.append("# --- Configure machine-level environment variables ---")
    commands.append(f"[Environment]::SetEnvironmentVariable('AI_API_KEY', '{api_key}', 'Machine')")
    commands.append(f"[Environment]::SetEnvironmentVariable('ADMIN_API_KEY', '{admin_key}', 'Machine')")
    commands.append(
        f"[Environment]::SetEnvironmentVariable('LICENSE_PUBLIC_KEY_PATH', '{_ps_quote(license_win)}', 'Machine')"
    )
    commands.append("[Environment]::SetEnvironmentVariable('LICENSE_ALGORITHM', 'ED25519', 'Machine')")

    if service_name:
        commands.append(f"Restart-Service -Name '{service_name}'")
    else:
        commands.append("Write-Host 'Restart the AI-Invoice process to load the new settings.'")

    if tls_cert_source and tls_cert_destination and tls_key_source and tls_key_destination:
        commands.append("")
        commands.append("# --- (Optional) Stage TLS materials for your reverse proxy ---")
        commands.append(
            f"New-Item -ItemType Directory -Path '{_ps_quote(PureWindowsPath(str(tls_cert_destination)).parent)}' -Force"
        )
        commands.append(
            f"Copy-Item '{_ps_quote(PureWindowsPath(str(tls_cert_source)))}' '{_ps_quote(PureWindowsPath(str(tls_cert_destination)))}' -Force"
        )
        commands.append(
            f"Copy-Item '{_ps_quote(PureWindowsPath(str(tls_key_source)))}' '{_ps_quote(PureWindowsPath(str(tls_key_destination)))}' -Force"
        )
        commands.append(
            "Write-Host 'Point IIS/NGINX at the staged certificate and key; the FastAPI app remains HTTP-only.'"
        )

    return "\n".join(commands)


def _build_linux_playbook(
    *,
    repo_keys: Path,
    license_destination: Path,
    secure_private: Path,
    api_key: str,
    admin_key: str,
    service_name: str,
    tls_cert_source: Path | None,
    tls_cert_destination: Path | None,
    tls_key_source: Path | None,
    tls_key_destination: Path | None,
) -> str:
    commands: list[str] = []

    commands.append("# --- Generate the Ed25519 keypair on your workstation ---")
    commands.append(f"cd '{_linux_quote(repo_keys)}'")
    commands.append("openssl genpkey -algorithm ed25519 -out license_private.pem")
    commands.append("openssl pkey -in license_private.pem -pubout -out license_public.pem")
    commands.append("")

    commands.append("# --- Archive the private key and shred the working copy ---")
    commands.append(f"install -m 0600 license_private.pem '{_linux_quote(secure_private)}'")
    commands.append("shred --remove license_private.pem")
    commands.append("")

    commands.append("# --- Stage the public verifier on the API host ---")
    commands.append(f"install -d -m 0750 '{_linux_quote(license_destination.parent)}'")
    commands.append(
        f"install -m 0640 license_public.pem '{_linux_quote(license_destination)}'"
    )
    commands.append("")

    commands.append("# --- Configure systemd environment overrides ---")
    override = textwrap.dedent(
        f"""
        [Service]
        Environment=AI_API_KEY={api_key}
        Environment=ADMIN_API_KEY={admin_key}
        Environment=LICENSE_PUBLIC_KEY_PATH={license_destination}
        Environment=LICENSE_ALGORITHM=ED25519
        """
    ).strip()
    commands.append("sudo mkdir -p /etc/systemd/system/{service}.d".format(service=service_name))
    commands.append(
        textwrap.dedent(
            """
            sudo tee /etc/systemd/system/{service}.d/override.conf >/dev/null <<'EOF'
            {override}
            EOF
            """
        ).strip().format(service=service_name, override=override)
    )
    commands.append("sudo systemctl daemon-reload")
    commands.append(f"sudo systemctl restart {service_name}")

    if tls_cert_source and tls_cert_destination and tls_key_source and tls_key_destination:
        commands.append("")
        commands.append("# --- (Optional) Stage TLS materials for your reverse proxy ---")
        commands.append(
            f"sudo install -d -m 0750 '{_linux_quote(tls_cert_destination.parent)}'"
        )
        commands.append(
            f"sudo install -m 0640 '{_linux_quote(tls_cert_source)}' '{_linux_quote(tls_cert_destination)}'"
        )
        commands.append(
            f"sudo install -m 0600 '{_linux_quote(tls_key_source)}' '{_linux_quote(tls_key_destination)}'"
        )
        commands.append(
            "echo 'Point your proxy (NGINX/HAProxy) at the staged certificate/key; the FastAPI app remains HTTP-only.'"
        )

    return "\n".join(commands)


def cmd_host_playbook(args: argparse.Namespace) -> None:
    repo_keys = Path(args.repo_keys).expanduser()
    license_destination = Path(args.license_destination).expanduser()
    secure_private = Path(args.secure_private).expanduser()

    tls_cert_source = Path(args.tls_cert_source).expanduser() if args.tls_cert_source else None
    tls_cert_destination = (
        Path(args.tls_cert_destination).expanduser() if args.tls_cert_destination else None
    )
    tls_key_source = Path(args.tls_key_source).expanduser() if args.tls_key_source else None
    tls_key_destination = (
        Path(args.tls_key_destination).expanduser() if args.tls_key_destination else None
    )

    tls_args = [
        tls_cert_source,
        tls_cert_destination,
        tls_key_source,
        tls_key_destination,
    ]
    if any(tls_args) and not all(tls_args):
        raise SystemExit(
            "TLS options require --tls-cert-source, --tls-cert-destination, --tls-key-source, and --tls-key-destination."
        )

    api_key = args.api_key or "$(openssl rand -hex 32)"
    admin_key = args.admin_key or args.api_key or "$(openssl rand -hex 32)"

    if args.os == "windows":
        output = _build_windows_playbook(
            repo_keys=repo_keys,
            license_destination=license_destination,
            secure_private=secure_private,
            api_key=api_key,
            admin_key=admin_key,
            service_name=args.service,
            tls_cert_source=tls_cert_source,
            tls_cert_destination=tls_cert_destination,
            tls_key_source=tls_key_source,
            tls_key_destination=tls_key_destination,
        )
    else:
        service_name = args.service or "ai-invoice.service"
        output = _build_linux_playbook(
            repo_keys=repo_keys,
            license_destination=license_destination,
            secure_private=secure_private,
            api_key=api_key,
            admin_key=admin_key,
            service_name=service_name,
            tls_cert_source=tls_cert_source,
            tls_cert_destination=tls_cert_destination,
            tls_key_source=tls_key_source,
            tls_key_destination=tls_key_destination,
        )

    print(output)


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
    systemd_parser.add_argument("--output", type=Path, help="Write override.conf to this path.")
    systemd_parser.add_argument(
        "--service",
        help="Name of the systemd service (used when printing follow-up commands).",
    )
    systemd_parser.set_defaults(func=cmd_systemd_override)

    stage_parser = subparsers.add_parser(
        "stage-assets",
        help="Copy the public license key (and optional TLS materials) into deployment directories.",
    )
    stage_parser.add_argument(
        "--license-public",
        type=Path,
        required=True,
        help="Source path to the generated license_public.pem file.",
    )
    stage_parser.add_argument(
        "--license-destination",
        type=Path,
        default=Path("/opt/ai-invoice/keys/license_public.pem"),
        help="Filesystem destination for the public verifier on the API host.",
    )
    stage_parser.add_argument("--api-key", help="AI_API_KEY to include in optional snippets.")
    stage_parser.add_argument(
        "--admin-key",
        help="ADMIN_API_KEY to include in optional snippets (defaults to API key placeholder).",
    )
    stage_parser.add_argument(
        "--license-algorithm",
        default="ed25519",
        help="License algorithm identifier to include in optional snippets.",
    )
    stage_parser.add_argument(
        "--pin-license-path",
        action="store_true",
        help="Print environment variable exports pointing at the destination path.",
    )
    stage_parser.add_argument(
        "--systemd-snippet",
        action="store_true",
        help="Render a sample systemd override block with the license path pinned.",
    )
    stage_parser.add_argument(
        "--tls-certificate",
        type=Path,
        help="Optional TLS certificate (PEM) to copy alongside the license key.",
    )
    stage_parser.add_argument(
        "--tls-key",
        type=Path,
        help="Optional TLS private key to copy alongside the license key.",
    )
    stage_parser.add_argument(
        "--tls-directory",
        type=Path,
        help="Destination directory for TLS assets (required when TLS files are provided).",
    )
    stage_parser.add_argument(
        "--tls-certificate-name",
        help="Filename to use when writing the TLS certificate (defaults to source name).",
    )
    stage_parser.add_argument(
        "--tls-key-name",
        help="Filename to use when writing the TLS private key (defaults to source name).",
    )
    stage_parser.set_defaults(func=cmd_stage_assets)

    playbook_parser = subparsers.add_parser(
        "host-playbook",
        help="Print end-to-end bootstrap commands for Windows or Linux hosts.",
    )
    playbook_parser.add_argument("--os", choices=("windows", "linux"), required=True, help="Target operating system.")
    playbook_parser.add_argument(
        "--repo-keys",
        required=True,
        help="Directory on the workstation that contains the keypair (e.g. the repo's keys folder).",
    )
    playbook_parser.add_argument(
        "--license-destination",
        required=True,
        help="Where the public verifier should reside on the API host.",
    )
    playbook_parser.add_argument(
        "--secure-private",
        required=True,
        help="Vault or secure share path where the private key should be archived.",
    )
    playbook_parser.add_argument("--api-key", help="AI_API_KEY value to include in the output (defaults to openssl rand).")
    playbook_parser.add_argument(
        "--admin-key",
        help="ADMIN_API_KEY value to include (defaults to the API key or another openssl rand command).",
    )
    playbook_parser.add_argument("--service", help="Service/process name to restart once environment variables are set.")
    playbook_parser.add_argument("--tls-cert-source", help="Source path to a TLS certificate to stage (optional).")
    playbook_parser.add_argument("--tls-cert-destination", help="Destination path for the staged TLS certificate (optional).")
    playbook_parser.add_argument("--tls-key-source", help="Source path to a TLS private key to stage (optional).")
    playbook_parser.add_argument("--tls-key-destination", help="Destination path for the staged TLS key (optional).")
    playbook_parser.set_defaults(func=cmd_host_playbook)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

