"""Admin authentication using HMAC-SHA256 signed tokens (JWT, HS256)."""
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)
_fallback_secret: str | None = None


def _secret() -> bytes:
    """Return the signing key. Without JWT_SECRET, a random per-process key is used,
    so tokens stop working when the API restarts or runs with several replicas."""
    global _fallback_secret
    configured = get_settings().JWT_SECRET
    if configured:
        return configured.encode()
    if _fallback_secret is None:
        logger.warning("JWT_SECRET is not set; using a random key. Set it in production.")
        _fallback_secret = secrets.token_urlsafe(32)
    return _fallback_secret.encode()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(signing_input: str) -> str:
    return _b64encode(hmac.new(_secret(), signing_input.encode(), hashlib.sha256).digest())


def create_token(subject: str = "admin") -> tuple[str, int]:
    """Create a signed token. Returns the token and its lifetime in seconds."""
    ttl = get_settings().TOKEN_TTL_MINUTES * 60
    now = int(time.time())
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64encode(json.dumps({"sub": subject, "iat": now, "exp": now + ttl}).encode())
    signing_input = f"{header}.{payload}"
    return f"{signing_input}.{_sign(signing_input)}", ttl


def verify_token(token: str) -> dict:
    """Verify signature and expiry. Raises ValueError on any problem."""
    try:
        header_b64, payload_b64, signature = token.split(".")
    except ValueError:
        raise ValueError("Malformed token")
    if not hmac.compare_digest(_sign(f"{header_b64}.{payload_b64}"), signature):
        raise ValueError("Invalid signature")
    try:
        header = json.loads(_b64decode(header_b64))
        payload = json.loads(_b64decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        raise ValueError("Malformed token")
    if header.get("alg") != "HS256":
        raise ValueError("Unsupported algorithm")
    if not isinstance(payload.get("exp"), int) or payload["exp"] < time.time():
        raise ValueError("Token expired")
    return payload


def check_password(password: str) -> bool:
    expected = get_settings().ADMIN_PASSWORD
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin login is disabled: ADMIN_PASSWORD is not configured",
        )
    return hmac.compare_digest(password.encode(), expected.encode())


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency that rejects requests without a valid admin token."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        return verify_token(credentials.credentials)
    except ValueError as exc:
        unauthorized.detail = str(exc)
        raise unauthorized
