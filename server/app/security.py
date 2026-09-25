"""Passwords, access tokens and device tokens."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from .config import settings

_hasher = PasswordHasher()

ALGORITHM = "HS256"
DEVICE_TOKEN_PREFIX = "gp_"


# --- passwords -------------------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return False


# Mirrors src/auth/validation.ts in the app, so the two never disagree about
# what a valid password is.
PASSWORD_MIN_LENGTH = 8


def password_problem(password: str) -> str | None:
    """Returns an error code, or None when the password is acceptable."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return "password_too_short"
    if not re.search(r"[A-Za-z]", password):
        return "password_needs_letter"
    return None


def normalise_email(email: str) -> str:
    return email.strip().lower()


# --- access tokens ---------------------------------------------------------


def create_access_token(user_id: str) -> tuple[str, int]:
    """Returns (jwt, seconds_until_expiry)."""
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "typ": "access",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> str | None:
    """Returns the user id, or None when the token is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


# --- refresh tokens --------------------------------------------------------


def create_refresh_token() -> tuple[str, str, datetime]:
    """Returns (plaintext, sha256, expiry). Only the hash reaches the database."""
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    return raw, sha256(raw), expires


# --- device tokens ---------------------------------------------------------


def create_device_token() -> tuple[str, str, str]:
    """Returns (plaintext, sha256, prefix).

    Shown to the grower once, at pairing, then only the hash is kept. These are
    high entropy random strings, so a single sha256 is the right primitive; the
    slow hashing argon2 does for passwords buys nothing here and would add
    latency to every reading a node uploads.
    """
    raw = DEVICE_TOKEN_PREFIX + secrets.token_urlsafe(32)
    return raw, sha256(raw), raw[:12]


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

