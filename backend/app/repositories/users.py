from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User


def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_by_telegram_id(db: Session, telegram_id: str) -> User | None:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def list_users(
    db: Session,
    *,
    role: str | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[User], int]:
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(User.full_name.ilike(like) | User.username.ilike(like))
    total = q.count()
    items = q.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return items, total
