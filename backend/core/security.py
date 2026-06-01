"""
Security utilities for password hashing and token generation.

Uses bcrypt for password hashing (via passlib) and secrets for token generation.
Falls back to hashlib-based hashing if passlib/bcrypt are not installed.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Tuple

logger = logging.getLogger("backend.core.security")

# Session token length (bytes) — 32 bytes = 256 bits
SESSION_TOKEN_BYTES = 32

# Minimum password length
MIN_PASSWORD_LENGTH = 6

# Session expiry (seconds) — 7 days
SESSION_EXPIRY_SECONDS = 7 * 24 * 3600

# Try to use passlib+bcrypt for production-grade hashing
_USE_BCRYPT = False
try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _USE_BCRYPT = True
except ImportError:
    logger.warning(
        "passlib[bcrypt] not installed — using SHA-256 password hashing fallback. "
        "Install with: pip install 'passlib[bcrypt]'"
    )
    _pwd_context = None


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    if _USE_BCRYPT and _pwd_context is not None:
        return _pwd_context.hash(password)
    # Fallback: salted SHA-256 (not production-grade, but functional)
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"sha256:{salt}:{hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    if _USE_BCRYPT and _pwd_context is not None:
        try:
            return _pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    # Fallback SHA-256 verification
    if not hashed_password.startswith("sha256:"):
        return False
    parts = hashed_password.split(":", 2)
    if len(parts) != 3:
        return False
    _, salt, stored_hash = parts
    computed = hashlib.sha256(f"{salt}:{plain_password}".encode()).hexdigest()
    return hmac.compare_digest(computed, stored_hash)


def generate_session_token() -> Tuple[str, str]:
    """
    Generate a new session token.

    Returns:
        Tuple of (raw_token, token_hash).
        The raw_token is sent to the client.
        The token_hash is stored in the database.
    """
    raw_token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def hash_session_token(raw_token: str) -> str:
    """Hash a raw session token for database lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def validate_email(email: str) -> str:
    """
    Basic email validation and normalization.

    Returns:
        Lowercased, stripped email.

    Raises:
        ValueError: If email format is invalid.
    """
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Invalid email format")
    local, domain = email.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        raise ValueError("Invalid email format")
    if len(email) > 255:
        raise ValueError("Email too long")
    return email


def validate_password(password: str) -> None:
    """
    Validate password meets minimum requirements.

    Raises:
        ValueError: If password is too short.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
