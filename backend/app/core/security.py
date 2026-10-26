from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings


settings = get_settings()

password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password securely."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return password_hash.verify(password, hashed_password)


def get_jwt_secret_key() -> str:
    """Resolve JWT secret key, allowing a secure test/dev fallback if unconfigured."""
    current_settings = get_settings()
    if current_settings.jwt_secret_key and current_settings.jwt_secret_key.strip():
        return current_settings.jwt_secret_key.strip()
    if current_settings.environment in ("development", "test"):
        return "term-shield-dev-secret-key-32chars-min-fallback!!"
    raise RuntimeError("JWT_SECRET_KEY is not configured in the server environment")


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    current_settings = get_settings()
    secret_key = get_jwt_secret_key()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=current_settings.access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    secret_key = get_jwt_secret_key()

    return jwt.decode(
        token,
        secret_key,
        algorithms=[ALGORITHM],
    )
