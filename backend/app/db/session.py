from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

_connect_args: dict = {}
_engine_kwargs: dict = {"echo": _settings.DATABASE_ECHO}

if _settings.DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    _engine_kwargs.update(
        pool_size=_settings.DB_POOL_SIZE,
        max_overflow=_settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )

engine = create_engine(
    _settings.DATABASE_URL,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
