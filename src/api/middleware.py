from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ai_invoice.config import Settings, settings
from ai_invoice.license import LicenseExpiredError, LicenseVerificationError
from ai_invoice.trial import TrialStatus, resolve_trial_claims
from .license_validator import HEADER_NAME, LicenseClaims, build_license_claims
from .security import get_license_verifier, require_license_token

LOGGER_NAME = "ai_invoice.api.middleware"


@dataclass
class _TokenBucket:
    tokens: float
    last_refill: float


class TokenBucketLimiter:
    """Simple token bucket limiter keyed by identity."""

    def __init__(self, rate_per_minute: int, burst: int | None = None) -> None:
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        burst_tokens = max(0, (burst or 0))
        self.rate_limit_per_minute = rate_per_minute
        self.rate_limit_burst = burst_tokens
        self.capacity = float(rate_per_minute + burst_tokens)
        self.refill_rate = float(rate_per_minute) / 60.0
        self._buckets: Dict[str, _TokenBucket] = {}

    def _refill(self, bucket: _TokenBucket, now: float) -> None:
        if now <= bucket.last_refill:
            return
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_rate)
        bucket.last_refill = now

    def allow(self, identity: str, *, now: float | None = None) -> bool:
        current_time = now if now is not None else time.monotonic()
        bucket = self._buckets.get(identity)
        if bucket is None:
            bucket = _TokenBucket(tokens=self.capacity, last_refill=current_time)
            self._buckets[identity] = bucket
        else:
            self._refill(bucket, current_time)

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True

        return False


def _is_authorized(header_value: str | None, config: Settings) -> bool:
    """Constant-time compare for API key when configured."""

    api_key = getattr(config, "api_key", None)
    if api_key:
        if header_value is None:
            return False
        return hmac.compare_digest(api_key, header_value)

    return bool(getattr(config, "allow_anonymous", False))


class APIKeyAndLoggingMiddleware(BaseHTTPMiddleware):
    """Validate API keys (except /health) and record basic request metrics."""

    def __init__(self, app: ASGIApp, *, config: Settings, logger: logging.Logger | None = None) -> None:
        super().__init__(app)
        self.config = config
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        rate_limit = getattr(config, "rate_limit_per_minute", None)
        if rate_limit and rate_limit > 0:
            burst = getattr(config, "rate_limit_burst", None)
            self._limiter = TokenBucketLimiter(rate_limit, burst)
        else:
            self._limiter = None

    def _requires_api_key(self, request: Request) -> bool:
        """Return True when the request must supply an API key."""

        method = request.method.upper()
        if method == "OPTIONS":
            # Always allow CORS preflight requests to proceed.
            return False

        path = request.url.path or "/"
        normalized = path.rstrip("/") or "/"

        # Public read-only resources that should remain accessible without an API key.
        if normalized in {"/", "/portal", "/admin", "/health"}:
            return False

        if path.startswith("/static/") or normalized == "/static":
            return False

        return True

    def _identity_from_request(self, request: Request) -> tuple[str, str]:
        license_header = request.headers.get(HEADER_NAME)
        if license_header:
            identity = f"license:{license_header}"
            label = "license"
        else:
            api_key_header = request.headers.get("X-API-Key")
            if api_key_header:
                identity = f"api_key:{api_key_header}"
                label = "api_key"
            else:
                client_host = request.client.host if request.client else "unknown"
                identity = f"client:{client_host}"
                label = "client"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        return identity, f"{label}:{digest}"

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        request.state.start_time = start
        request.state.rate_limited = False
        request.state.identity_hash = None
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        response: Response | None = None
        try:
            # Allow health without auth (both /health and /health/)
            claims: LicenseClaims | None = None
            trial_status: TrialStatus | None = None
            trial_error: str | None = None
            requires_api_key = self._requires_api_key(request)
            if requires_api_key:
                header = request.headers.get("X-API-Key")
                if not _is_authorized(header, self.config):
                    status_code = status.HTTP_401_UNAUTHORIZED
                    response = JSONResponse({"detail": "Unauthorized"}, status_code=status_code)
                    return response
                if self._limiter is not None:
                    identity, identity_hash = self._identity_from_request(request)
                    request.state.identity_hash = identity_hash
                    allowed = self._limiter.allow(identity)
                    if not allowed:
                        status_code = status.HTTP_429_TOO_MANY_REQUESTS
                        request.state.rate_limited = True
                        throttle_log = {
                            "event": "rate_limit_exceeded",
                            "identity_hash": identity_hash,
                            "throttled": True,
                            "status_code": status_code,
                            "rate_limit_per_minute": self._limiter.rate_limit_per_minute,
                            "rate_limit_burst": self._limiter.rate_limit_burst,
                        }
                        self.logger.warning(
                            "Rate limit exceeded for identity %s",
                            identity_hash,
                            extra=throttle_log,
                        )
                        response = JSONResponse(
                            {"detail": "Too Many Requests"}, status_code=status_code
                        )
                        return response

                if getattr(self.config, "license_public_key_path", None):
                    token = request.headers.get(HEADER_NAME)
                    if token is None or not token.strip():
                        status_code = status.HTTP_401_UNAUTHORIZED
                        response = JSONResponse(
                            {"detail": "Missing license token."}, status_code=status_code
                        )
                        return response

                    try:
                        verifier = get_license_verifier()
                    except Exception:
                        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                        response = JSONResponse(
                            {"detail": "License verification is not configured."},
                            status_code=status_code,
                        )
                        return response

                    try:
                        payload = verifier.verify_token(token.strip())
                    except LicenseExpiredError:
                        status_code = status.HTTP_403_FORBIDDEN
                        response = JSONResponse(
                            {"detail": "License token expired."}, status_code=status_code
                        )
                        return response
                    except LicenseVerificationError:
                        status_code = status.HTTP_401_UNAUTHORIZED
                        response = JSONResponse(
                            {"detail": "Invalid license token."}, status_code=status_code
                        )
                        return response

                    try:
                        claims = build_license_claims(payload, config=self.config)
                    except HTTPException as exc:
                        status_code = exc.status_code
                        response = JSONResponse({"detail": exc.detail}, status_code=status_code)
                        return response
                else:
                    trial_status, trial_claims = resolve_trial_claims()
                    if trial_claims is not None:
                        claims = LicenseClaims(raw=dict(trial_claims), features=frozenset(trial_status.features))
                    else:
                        trial_error = (
                            "Trial period has expired. Advanced features are disabled until a license is applied."
                        )

            request.state.api_key_valid = True
            request.state.license_claims = claims
            if trial_status is not None:
                request.state.trial_status = trial_status
            if trial_error is not None:
                request.state.trial_error_detail = trial_error
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            self.logger.exception("Unhandled error while processing request")
            raise
        finally:
            end = time.perf_counter()
            duration = end - start
            request.state.end_time = end
            request.state.duration = duration
            log_data: dict[str, Any] = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration": duration,
                "duration_ms": round(duration * 1000, 3),
            }
            if getattr(request.state, "identity_hash", None):
                log_data["identity_hash"] = request.state.identity_hash
            log_data["throttled"] = bool(getattr(request.state, "rate_limited", False))
            if self._limiter is not None:
                log_data["rate_limit_per_minute"] = self._limiter.rate_limit_per_minute
                log_data["rate_limit_burst"] = self._limiter.rate_limit_burst
            self.logger.info(
                "%s %s -> %s in %.3f ms",
                request.method,
                request.url.path,
                status_code,
                duration * 1000,
                extra=log_data,
            )


def require_api_key(request: Request) -> None:
    """Dependency to enforce API key validation for specific routes."""
    # Skip health explicitly
    if request.url.path.rstrip("/") == "/health":
        return
    if not _is_authorized(request.headers.get("X-API-Key"), settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the configured size.

    Uses Content-Length when provided (cheap path); otherwise lets downstream
    framework handle streaming limits.
    """

    def __init__(self, app: ASGIApp, *, max_len: int = 20 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_len = max_len

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_len:
                    raise HTTPException(status_code=413, detail="Payload too large")
            except ValueError:
                # If header is malformed, let the request proceed; FastAPI will handle it.
                pass
        return await call_next(request)


def configure_middleware(app: FastAPI) -> None:
    # API key + timing/logging
    app.add_middleware(APIKeyAndLoggingMiddleware, config=settings)

    # Body size limit (fallback to default if not present in settings)
    max_len = int(getattr(settings, "max_upload_bytes", 20 * 1024 * 1024))
    app.add_middleware(BodyLimitMiddleware, max_len=max_len)

    # CORS
    trusted_origins = getattr(settings, "cors_trusted_origins", [])
    if trusted_origins:
        allow_origins = list(dict.fromkeys(origin.origin for origin in trusted_origins))
        allow_credentials = any(origin.allow_credentials for origin in trusted_origins)
    else:
        allow_origins = ["*"]
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Convenience list for route-level dependency injection if desired:
Dependencies = [Depends(require_api_key), Depends(require_license_token)]
