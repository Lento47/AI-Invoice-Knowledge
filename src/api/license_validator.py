from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from fastapi import HTTPException, Request, status

from ai_invoice.config import Settings, settings


HEADER_NAME = "X-License"
_DIGEST_INFO_SHA256 = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)


@dataclass(frozen=True, slots=True)
class LicenseClaims:
    """Validated license claims attached to incoming requests."""

    raw: Mapping[str, Any]
    features: frozenset[str]

    def __getitem__(self, item: str) -> Any:
        return self.raw[item]

    def get(self, item: str, default: Any | None = None) -> Any:
        return self.raw.get(item, default)

    @property
    def expires_at(self) -> datetime | None:
        exp = self.raw.get("exp")
        if isinstance(exp, (int, float)):
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None

    def has_feature(self, feature: str) -> bool:
        return feature in self.features


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _normalize_features(value: Any) -> frozenset[str]:
    if isinstance(value, str):
        candidates: Sequence[str] = [value]
    elif isinstance(value, Sequence):
        candidates = value
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License payload is missing feature permissions.",
        )

    normalized = [item.strip() for item in candidates if isinstance(item, str) and item.strip()]
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License payload is missing feature permissions.",
        )
    return frozenset(normalized)


def _read_length(buffer: bytes, offset: int) -> tuple[int, int]:
    first = buffer[offset]
    offset += 1
    if first & 0x80 == 0:
        return first, offset
    num_bytes = first & 0x7F
    length = int.from_bytes(buffer[offset : offset + num_bytes], "big")
    offset += num_bytes
    return length, offset


def _read_der_element(buffer: bytes, offset: int) -> tuple[int, bytes, int]:
    tag = buffer[offset]
    offset += 1
    length, offset = _read_length(buffer, offset)
    value = buffer[offset : offset + length]
    offset += length
    return tag, value, offset


def _load_rsa_public_numbers(pem: str) -> tuple[int, int]:
    body = "".join(line.strip() for line in pem.strip().splitlines() if "-----" not in line)
    der = base64.b64decode(body)

    tag, value, _ = _read_der_element(der, 0)
    if tag != 0x30:
        raise ValueError("Invalid public key: expected SEQUENCE")

    inner_offset = 0
    alg_tag, alg_value, inner_offset = _read_der_element(value, inner_offset)
    if alg_tag != 0x30:
        raise ValueError("Invalid public key: missing algorithm identifier")
    bitstring_tag, bitstring_value, _ = _read_der_element(value, inner_offset)
    if bitstring_tag != 0x03 or not bitstring_value:
        raise ValueError("Invalid public key: missing public key bit string")
    if bitstring_value[0] != 0x00:
        raise ValueError("Invalid public key: unexpected padding bits")

    rsa_der = bitstring_value[1:]
    rsa_tag, rsa_value, _ = _read_der_element(rsa_der, 0)
    if rsa_tag != 0x30:
        raise ValueError("Invalid public key: malformed RSA structure")

    offset = 0
    mod_tag, mod_value, offset = _read_der_element(rsa_value, offset)
    exp_tag, exp_value, _ = _read_der_element(rsa_value, offset)
    if mod_tag != 0x02 or exp_tag != 0x02:
        raise ValueError("Invalid public key: malformed RSA integers")

    modulus = int.from_bytes(mod_value, "big")
    exponent = int.from_bytes(exp_value, "big")
    return modulus, exponent


def _verify_rs256(signing_input: bytes, signature: bytes, modulus: int, exponent: int) -> bool:
    expected_hash = _DIGEST_INFO_SHA256 + hashlib.sha256(signing_input).digest()

    modulus_len = (modulus.bit_length() + 7) // 8
    signature_int = int.from_bytes(signature, "big")
    recovered = pow(signature_int, exponent, modulus)
    recovered_bytes = recovered.to_bytes(modulus_len, "big")

    if len(recovered_bytes) < len(expected_hash) + 11:
        return False
    if not recovered_bytes.startswith(b"\x00\x01"):
        return False
    try:
        separator_index = recovered_bytes.index(b"\x00", 2)
    except ValueError:
        return False
    padding = recovered_bytes[2:separator_index]
    if len(padding) < 8 or any(byte != 0xFF for byte in padding):
        return False
    return recovered_bytes[separator_index + 1 :] == expected_hash


def _parse_jwt_segments(token: str) -> tuple[str, str, str]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid license token.")
    return parts[0], parts[1], parts[2]


def _decode_json(segment: str) -> Mapping[str, Any]:
    try:
        data = json.loads(_b64url_decode(segment))
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid license token.")
    if not isinstance(data, Mapping):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid license token.")
    return data


def validate_license_token(
    token: str | None,
    *,
    config: Settings | None = None,
) -> LicenseClaims:
    """Validate a signed license token and return normalized claims."""

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing license token.")

    cfg = config or settings
    key = getattr(cfg, "license_public_key", None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="License verification is not configured.",
        )

    header_segment, payload_segment, signature_segment = _parse_jwt_segments(token)
    header = _decode_json(header_segment)
    payload = _decode_json(payload_segment)

    algorithm = (header.get("alg") or "").upper()
    expected_alg = (getattr(cfg, "license_algorithm", "RS256") or "RS256").upper()
    if algorithm != expected_alg:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid license token.")

    try:
        modulus, exponent = _load_rsa_public_numbers(key)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Invalid license key.") from exc

    signature = _b64url_decode(signature_segment)
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    if not _verify_rs256(signing_input, signature, modulus, exponent):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid license token.")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token missing expiry.")
    if exp < time.time():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token expired.")

    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token missing identifier.")
    if jti in getattr(cfg, "license_revoked_jtis", frozenset()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token revoked.")

    subject = payload.get("sub")
    if isinstance(subject, str) and subject in getattr(cfg, "license_revoked_subjects", frozenset()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License token revoked.")

    features = _normalize_features(payload.get("features"))

    return LicenseClaims(raw=dict(payload), features=features)


def ensure_feature(claims: LicenseClaims | None, feature: str) -> LicenseClaims:
    """Ensure the provided claims include a specific feature permission."""

    normalized = feature.strip()
    if not normalized:
        raise ValueError("Feature name must be a non-empty string.")
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing license token.")
    if normalized not in claims.features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"License does not permit '{normalized}' operations.",
        )
    return claims


def get_license_claims(request: Request) -> LicenseClaims:
    trial_error = getattr(request.state, "trial_error_detail", None)
    if isinstance(trial_error, str) and trial_error.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=trial_error)
    claims = getattr(request.state, "license_claims", None)
    if not isinstance(claims, LicenseClaims):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing license token.")
    return claims


def require_feature_flag(feature: str) -> Callable[[Request], LicenseClaims]:
    """FastAPI dependency that enforces the presence of a license feature."""

    def _dependency(request: Request) -> LicenseClaims:
        claims = get_license_claims(request)
        return ensure_feature(claims, feature)

    return _dependency
