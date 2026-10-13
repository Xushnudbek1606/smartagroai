from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Annotated, Iterable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import forbidden, too_many_requests, unauthorized
from app.core.security import decode_token
from app.db.session import get_db
from app.models import AuditLog, User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]

ROLE_ADMIN = "admin"
ROLE_FARMER = "farmer"
ROLE_AGRONOM = "agronom"
ALL_ROLES = (ROLE_ADMIN, ROLE_FARMER, ROLE_AGRONOM)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise unauthorized("Authentication required", "missing_token")
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except Exception:
        raise unauthorized("Invalid or expired token", "invalid_token")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise unauthorized("User no longer exists", "user_not_found")
    if not user.is_active:
        raise forbidden("Account is deactivated", "account_deactivated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise forbidden("You do not have permission to perform this action", "insufficient_role")
        return user

    return checker


def require_fresh_password(user: CurrentUser) -> User:
    """Block non-essential endpoints until the temporary password is replaced."""
    if user.must_change_password:
        raise forbidden(
            "You must change your password before continuing", "password_change_required"
        )
    return user


FreshUser = Annotated[User, Depends(require_fresh_password)]


class RateLimiter:
    """Simple in-memory sliding-window limiter (per-process).

    Good enough for a single API process; swap for Redis in multi-replica deployments.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                raise too_many_requests("Too many requests, please try again later", "rate_limited")
            q.append(now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


rate_limiter = RateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def audit(
    db: Session,
    actor_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """Record an administrative/security relevant action. Never log secrets here."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )
