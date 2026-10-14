from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header

from app.core.config import get_settings
from app.core.security import constant_time_equals
from app.db.session import SessionLocal
from app.models import SystemEvent, User
from app.schemas import (
    InvitationClaimOut,
    InvitationClaimRequest,
    InvitationStatusOut,
    TelegramHeartbeat,
    TelegramLanguageRequest,
    TelegramPreferencesRequest,
)
from app.services import invitation_service

router = APIRouter(prefix="/internal", tags=["internal"])


def require_bot_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Internal API disabled (secret not configured)")
    if not x_internal_secret or not constant_time_equals(x_internal_secret, settings.TELEGRAM_WEBHOOK_SECRET):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid internal secret")


secret_dep = Depends(require_bot_secret)


@router.post("/telegram/claim", response_model=InvitationClaimOut, dependencies=[secret_dep])
def claim(body: InvitationClaimRequest) -> InvitationClaimOut:
    """Bot sends the one-time code + telegram id; backend links the account
    and returns login + one-time password for delivery to the private chat."""
    result = invitation_service.claim_invitation(
        SessionLocal(),
        code=body.code,
        telegram_id=body.telegram_id,
        telegram_username=body.telegram_username,
    )
    return InvitationClaimOut(**result)


SUPPORTED_LANGUAGES = ("uz-Latn", "uz-Cyrl", "en", "ru")


@router.get("/telegram/status", response_model=InvitationStatusOut, dependencies=[secret_dep])
def telegram_status(telegram_id: str) -> InvitationStatusOut:
    return InvitationStatusOut(
        **invitation_service.invitation_status(SessionLocal(), telegram_id=telegram_id)
    )


@router.get("/telegram/user", dependencies=[secret_dep])
def telegram_user(telegram_id: str, telegram_username: str | None = None) -> dict:
    """Identity of the Telegram account behind a chat. The bot passes the
    current @username so the stored binding follows Telegram: if the user
    later sets or renames their username, the platform record is refreshed
    instead of going stale (the stable key stays telegram_id)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user is None:
            return {"found": False}
        if telegram_username:
            cleaned = telegram_username.strip().lstrip("@")
            if cleaned and cleaned != user.telegram_username:
                user.telegram_username = cleaned
                db.add(user)
                db.commit()
        return {
            "found": True,
            "username": user.username,
            "language": user.preferred_language,
            "full_name": user.full_name,
            "role": user.role,
            "region": user.region,
            "district": user.district,
            "telegram_username": user.telegram_username,
            "notifications_enabled": user.telegram_notifications_enabled,
        }
    finally:
        db.close()


@router.post("/telegram/language", dependencies=[secret_dep])
def set_language(body: TelegramLanguageRequest) -> dict:
    """Bot /language choice persists to the user's profile so every surface
    (web, bot, notifications) follows one language."""
    if body.language not in SUPPORTED_LANGUAGES:
        return {"status": "unsupported", "language": body.language}
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == body.telegram_id).first()
        if user is None:
            return {"status": "not_linked"}
        user.preferred_language = body.language
        db.add(user)
        db.commit()
        return {"status": "ok", "language": body.language}
    finally:
        db.close()


@router.post("/telegram/heartbeat", dependencies=[secret_dep])
def heartbeat(body: TelegramHeartbeat) -> dict:
    db = SessionLocal()
    try:
        db.add(
            SystemEvent(
                kind="telegram_bot_heartbeat",
                payload={
                    "bot_started_at": body.bot_started_at.isoformat() if body.bot_started_at else None,
                    "version": body.version,
                },
            )
        )
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}


@router.post("/telegram/preferences", dependencies=[secret_dep])
def set_preferences(body: TelegramPreferencesRequest) -> dict:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == body.telegram_id).first()
        if user is None:
            return {"status": "not_linked"}
        user.telegram_notifications_enabled = body.enabled
        db.add(user)
        db.commit()
        return {"status": "ok", "enabled": body.enabled}
    finally:
        db.close()


@router.get("/telegram/weather", dependencies=[secret_dep])
def bot_weather(location: str) -> dict:
    """Weather for the bot: read-only cache access; returns cached payload
    only — the bot never fabricates data either."""
    from app.integrations.weather import WeatherServiceError, weather_service
    from app.models import WeatherCache

    db = SessionLocal()
    try:
        try:
            return weather_service.current(db, location)
        except WeatherServiceError as err:
            return {"error": {"code": err.code, "message": err.message}}
    finally:
        db.close()
