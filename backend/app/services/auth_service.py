from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request, unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models import RefreshToken, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_refresh(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_tokens(db: Session, user: User) -> dict:
    settings = get_settings()
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_refresh(refresh),
            expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(user.password_hash, password):
        raise unauthorized("Incorrect username or password", "invalid_credentials")
    if not user.is_active:
        raise unauthorized("This account has been deactivated", "account_deactivated")
    return user


def rotate_refresh_token(db: Session, refresh_token: str) -> dict:
    stored = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_refresh(refresh_token)).first()
    )
    if stored is None or stored.revoked_at is not None:
        raise unauthorized("Invalid refresh token", "invalid_refresh_token")
    expires = stored.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < _utcnow():
        raise unauthorized("Refresh token expired", "refresh_token_expired")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise unauthorized("Account unavailable", "account_deactivated")
    stored.revoked_at = _utcnow()
    return issue_tokens(db, user)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    stored = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == _hash_refresh(refresh_token)).first()
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = _utcnow()
        db.commit()


def revoke_all_for_user(db: Session, user_id: str) -> None:
    now = _utcnow()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now})
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(user.password_hash, current_password):
        raise bad_request("Current password is incorrect", "wrong_current_password")
    if verify_password(user.password_hash, new_password):
        raise bad_request("New password must be different from the current one", "same_password")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = _utcnow()
    db.add(user)
    db.commit()
    revoke_all_for_user(db, user.id)
