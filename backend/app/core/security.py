"""
Security primitives — password hashing, JWT tokens, password reset tokens.

Uses bcrypt for password hashing and PyJWT for JSON Web Tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Password Hashing ───────────────────────────────────────────────────────

BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password.

    Returns:
        The bcrypt hash string prefixed with $2b$.
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed: bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        plaintext: The plaintext password to check.
        hashed: The stored bcrypt hash.

    Returns:
        True if the password matches.
    """
    return bcrypt.checkpw(
        plaintext.encode("utf-8"),
        hashed.encode("utf-8"),
    )


# ── JWT Token Management ───────────────────────────────────────────────────

ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The token subject (user ID).
        extra_claims: Additional claims to embed.
        expires_delta: Token expiry (default from config: 30 minutes).

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str,
    token_id: str | None = None,
) -> str:
    """
    Create a JWT refresh token with longer expiry.

    Args:
        subject: The token subject (user ID).
        token_id: Optional unique token ID for rotation tracking.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }

    if token_id:
        payload["jti"] = token_id

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.PyJWTError: Token is invalid.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


# ── Password Reset Tokens ──────────────────────────────────────────────────


def create_password_reset_token(user_id: str) -> str:
    """
    Create a short-lived JWT for password reset.

    Args:
        user_id: The user ID requesting the reset.

    Returns:
        Encoded JWT string (24-hour expiry by default).
    """
    expire = datetime.now(UTC) + timedelta(
        hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
    )

    payload: dict[str, Any] = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "password_reset",
        "purpose": "password_reset",
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_password_reset_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a password reset token.

    Args:
        token: The password reset JWT.

    Returns:
        Decoded payload if valid.

    Raises:
        jwt.ExpiredSignatureError: Token expired.
        jwt.PyJWTError: Token invalid.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

    if payload.get("type") != "password_reset" or payload.get("purpose") != "password_reset":
        raise jwt.PyJWTError("Invalid token purpose")

    return payload


# ── Utilities ──────────────────────────────────────────────────────────────


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe Content-Disposition and filesystem use.

    Strips path separators, control characters, and limits extension length.
    """
    # Remove path separators
    safe = filename.replace("/", "_").replace("\\", "_")
    # Remove null bytes and control characters
    safe = "".join(c for c in safe if c.isprintable() and ord(c) >= 32)
    # Limit total length
    safe = safe[:255]
    return safe or "unnamed"


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_hex(length)


def create_api_key() -> str:
    """Generate a URL-safe prefixed API key."""
    return f"et_{secrets.token_urlsafe(32)}"


def generate_token_id() -> str:
    """Generate a unique token ID for refresh token tracking."""
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    """
    Hash a token for storage using HMAC-SHA256.

    Args:
        token: The token string to hash.

    Returns:
        Hex-encoded HMAC-SHA256 digest.
    """
    return hmac.new(
        key=settings.SECRET_KEY.encode(),
        msg=token.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_token(token: str, hashed: str) -> bool:
    """
    Verify a token against its stored hash.

    Args:
        token: The token to verify.
        hashed: The stored hash to compare against.

    Returns:
        True if the token matches.
    """
    return hmac.compare_digest(hash_token(token), hashed)
