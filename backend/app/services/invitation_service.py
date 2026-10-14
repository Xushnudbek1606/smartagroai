from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request, conflict, forbidden, not_found, unauthorized
from app.core.security import (
    generate_one_time_code,
    generate_temp_password,
    hash_code,
    hash_password,
    verify_code_hash,
)
from app.models import Invitation, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_invitation(
    db: Session, *, user_id: str, created_by: str | None, purpose: str = "telegram_link"
) -> dict:
    settings = get_settings()
    # Invalidate previous unused invitations for the same user/purpose
    db.query(Invitation).filter(
        Invitation.user_id == user_id,
        Invitation.purpose == purpose,
        Invitation.used_at.is_(None),
    ).update({"expires_at": _utcnow()})
    code = generate_one_time_code()
    expires_at = _utcnow() + timedelta(minutes=settings.INVITATION_EXPIRE_MINUTES)
    inv = Invitation(
        user_id=user_id,
        token_hash=hash_code(code),
        purpose=purpose,
        expires_at=expires_at,
        created_by=created_by,
    )
    db.add(inv)
    db.flush()
    return {"invitation": inv, "code": code, "expires_at": expires_at}


def claim_invitation(
    db: Session, *, code: str, telegram_id: str, telegram_username: str | None
) -> dict:
    """Validate a one-time code, link the Telegram account and mint a
    one-time password. The raw password is returned once so the bot can
    deliver it into the owner's private chat; only its hash is stored."""
    candidates = (
        db.query(Invitation)
        .filter(Invitation.used_at.is_(None), Invitation.purpose == "telegram_link")
        .all()
    )
    match: Invitation | None = None
    for inv in candidates:
        if verify_code_hash(inv.token_hash, code):
            match = inv
            break
    if match is None:
        raise unauthorized("Invitation code is invalid", "invalid_invitation_code")

    expires = match.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < _utcnow():
        raise bad_request("Invitation code has expired", "invitation_expired")

    # A Telegram account may be linked to only one user
    existing = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing is not None:
        raise conflict("This Telegram account is already linked", "telegram_already_linked")

    user = db.get(User, match.user_id)
    if user is None:
        raise not_found("User no longer exists")
    if not user.is_active:
        raise bad_request("This account is deactivated", "account_deactivated")

    # Pre-binding: when the admin saved a @username in advance, only that
    # Telegram account may complete the claim — the code is useless if a
    # stranger gets hold of it.
    if user.telegram_username:
        expected = user.telegram_username.lstrip("@").lower()
        got = (telegram_username or "").lstrip("@").lower()
        if got != expected:
            raise forbidden(
                "This code belongs to a different Telegram account",
                "telegram_username_mismatch",
            )

    temp_password = generate_temp_password()
    user.telegram_id = telegram_id
    # keep the @username as a stable hint (may be None if Telegram hides it)
    user.telegram_username = telegram_username
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True
    db.add(user)

    match.used_at = _utcnow()
    match.telegram_id_at_use = telegram_id
    db.add(match)
    db.commit()
    return {
        "username": user.username,
        "temporary_password": temp_password,
        "language": user.preferred_language,
        "full_name": user.full_name,
    }


def invitation_status(db: Session, *, telegram_id: str) -> dict:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user is None:
        return {"linked": False, "username": None, "language": None}
    return {"linked": True, "username": user.username, "language": user.preferred_language}
