from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt import PyJWTError

from app.core.config import get_settings

_hasher = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=2)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:  # pragma: no cover - defensive
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except Exception:  # pragma: no cover
        return False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    return create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"role": role},
    )


def create_refresh_token(user_id: str) -> str:
    settings = get_settings()
    return create_token(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises jwt.PyJWTError on any failure."""
    settings = get_settings()
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    if payload.get("type") != expected_type:
        raise PyJWTError("unexpected token type")
    return payload


def generate_one_time_code(length: int = 8) -> str:
    """Human-friendly, unambiguous one-time code (no 0/O/1/I)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_temp_password(length: int = 12) -> str:
    """High-entropy temporary password delivered once via Telegram."""
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_code(code: str) -> str:
    """One-way hash for one-time codes (constant comparison done by caller)."""
    return _hasher.hash(code.strip().upper())


def verify_code_hash(hashed: str, code: str) -> bool:
    try:
        return _hasher.verify(hashed, code.strip().upper())
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:  # pragma: no cover
        return False


def constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
