"""
Password hashing and JWT access token utilities.

Password hashing uses Argon2id (via argon2-cffi) with its library
defaults, which follow OWASP's current recommendation — no manual
cost-parameter tuning here; that's a real way to accidentally weaken it.

Token strategy (v0.2 decision, recorded here rather than left implicit):
a single short-lived JWT access token, delivered via an HttpOnly cookie.
No refresh-token rotation in v0.2 — sessions simply expire and require
re-login. Refresh tokens are meaningful v0.7-hardening scope, not v0.2;
adding them now would be exactly the kind of premature complexity the
project has been deliberately avoiding at each milestone.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> uuid.UUID:
    """Returns the user id encoded in a valid, unexpired token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError from exc
