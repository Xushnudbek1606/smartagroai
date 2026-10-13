from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.deps import DbSession, audit, require_roles
from app.core.errors import not_found
from app.models import (
    AgronomAssignment,
    AuditLog,
    Conversation,
    Crop,
    Diagnosis,
    Farm,
    Message,
    Notification,
    Setting,
    SystemEvent,
    User,
)
from app.schemas import (
    AdminStatisticsOut,
    AuditLogOut,
    IntegrationStatusOut,
    Page,
    SettingsOut,
    SettingsUpdate,
    SystemHealthOut,
    TelegramHeartbeat,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/statistics", response_model=AdminStatisticsOut)
def statistics(db: DbSession, user: User = Depends(require_roles("admin"))) -> AdminStatisticsOut:
    now = _utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    def count(model, *filters) -> int:
        q = db.query(model)
        for f in filters:
            q = q.filter(f)
        return q.count()

    activity: list[dict[str, Any]] = []
    for i in range(13, -1, -1):
        day = (day_start - timedelta(days=i)).date()
        next_day = day + timedelta(days=1)
        activity.append(
            {
                "date": day.isoformat(),
                "diagnoses": count(
                    Diagnosis,
                    Diagnosis.created_at >= datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
                    Diagnosis.created_at < datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc),
                ),
                "registrations": count(
                    User,
                    User.created_at >= datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
                    User.created_at < datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc),
                ),
            }
        )

    return AdminStatisticsOut(
        total_users=count(User),
        total_farmers=count(User, User.role == "farmer"),
        total_agronomists=count(User, User.role == "agronom"),
        total_admins=count(User, User.role == "admin"),
        active_users=count(User, User.is_active.is_(True)),
        total_farms=count(Farm),
        total_crops=count(Crop),
        total_diagnoses=count(Diagnosis),
        diagnoses_today=count(Diagnosis, Diagnosis.created_at >= day_start),
        diagnoses_week=count(Diagnosis, Diagnosis.created_at >= week_start),
        total_conversations=count(Conversation),
        messages_total=count(Message),
        users_registered_today=count(User, User.created_at >= day_start),
        activity=activity,
    )


@router.get("/audit-logs", response_model=Page[AuditLogOut])
def audit_logs(
    db: DbSession,
    user: User = Depends(require_roles("admin")),
    action: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
) -> Page[AuditLogOut]:
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    rows: list[AuditLogOut] = []
    for log in items:
        out = AuditLogOut.model_validate(log)
        actor = db.get(User, log.actor_id) if log.actor_id else None
        out.actor_name = actor.full_name if actor else None
        rows.append(out)
    return Page[AuditLogOut](
        items=rows, total=total, page=page, page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/system-health", response_model=SystemHealthOut)
def system_health(db: DbSession, user: User = Depends(require_roles("admin"))) -> SystemHealthOut:
    # NB: keep this distinct from the Setting model / SettingsOut schema — a bare
    # `settings` name here would shadow the config object and confuse readers.
    app_settings = get_settings()
    from sqlalchemy import text

    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    heartbeat = (
        db.query(SystemEvent)
        .filter(SystemEvent.kind == "telegram_bot_heartbeat")
        .order_by(SystemEvent.created_at.desc())
        .first()
    )
    bot_online = False
    bot_detail: dict[str, Any] = {"configured": app_settings.telegram_configured}
    if heartbeat and heartbeat.created_at:
        started = heartbeat.created_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        bot_online = (_utcnow() - started) < timedelta(minutes=5)
        bot_detail["last_heartbeat"] = started.isoformat()
    bot_detail["online"] = bot_online

    try:
        import redis as redis_lib

        if app_settings.REDIS_URL:
            r = redis_lib.from_url(app_settings.REDIS_URL, socket_connect_timeout=2)
            r.ping()
            redis_status = "ok"
        else:
            redis_status = "not_configured"
    except Exception:
        redis_status = "error"

    statuses = [db_status, "ok" if app_settings.ai_configured else "not_configured",
                "ok" if app_settings.weather_configured else "not_configured"]
    overall = "ok" if all(s in ("ok", "not_configured") for s in statuses) else "degraded"
    if db_status == "error":
        overall = "error"

    return SystemHealthOut(
        status=overall,
        database=db_status,
        weather_api=IntegrationStatusOut(
            configured=app_settings.weather_configured,
            provider=app_settings.WEATHER_PROVIDER if app_settings.weather_configured else None,
        ),
        ai_service=IntegrationStatusOut(
            configured=app_settings.ai_configured,
            provider=app_settings.AI_PROVIDER if app_settings.ai_configured else None,
            model=app_settings.AI_MODEL_NAME if app_settings.ai_configured else None,
        ),
        telegram_bot=bot_detail,
        redis=redis_status,
        environment=app_settings.ENVIRONMENT,
        checked_at=_utcnow(),
    )


@router.get("/settings", response_model=SettingsOut)
def get_settings_admin(db: DbSession, user: User = Depends(require_roles("admin"))) -> SettingsOut:
    rows = db.query(Setting).all()
    return SettingsOut(settings={r.key: r.value for r in rows})


@router.patch("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, db: DbSession, user: User = Depends(require_roles("admin"))) -> SettingsOut:
    for key, value in body.settings.items():
        row = db.query(Setting).filter(Setting.key == key).first()
        if row is None:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value
            db.add(row)
    audit(db, user.id, "admin.settings_updated", detail={"keys": list(body.settings.keys())})
    db.commit()
    rows = db.query(Setting).all()
    return SettingsOut(settings={r.key: r.value for r in rows})
