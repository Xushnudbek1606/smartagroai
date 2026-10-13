from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.core.errors import not_found
from app.models import Notification
from app.schemas import MessageOut, NotificationOut, Page

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationOut])
def list_notifications(
    db: DbSession,
    user: CurrentUser,
    unread_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[NotificationOut]:
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    total = q.count()
    items = (
        q.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page[NotificationOut](
        items=[NotificationOut.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/unread-count", response_model=dict)
def unread_count(db: DbSession, user: CurrentUser) -> dict:
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, db: DbSession, user: CurrentUser) -> NotificationOut:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise not_found("Notification not found")
    n.is_read = True
    db.add(n)
    db.commit()
    db.refresh(n)
    return NotificationOut.model_validate(n)


@router.post("/read-all", response_model=MessageOut)
def mark_all_read(db: DbSession, user: CurrentUser) -> MessageOut:
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return MessageOut(detail="All notifications marked as read")
