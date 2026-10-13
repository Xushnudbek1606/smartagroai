from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User

logger = logging.getLogger(__name__)


def ensure_admin(db: Session) -> None:
    """Create the initial admin account from env vars if it does not exist.

    Controlled by SEED_ADMIN_USERNAME / SEED_ADMIN_PASSWORD (see .env.example).
    """
    settings = get_settings()
    import os

    username = os.getenv("SEED_ADMIN_USERNAME", "admin")
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        return
    if not password:
        logger.info("SEED_ADMIN_PASSWORD not set; skipping admin seed")
        return
    admin = User(
        full_name="Platform Administrator",
        username=username,
        password_hash=hash_password(password),
        role="admin",
        preferred_language="uz-Latn",
        is_active=True,
        must_change_password=False,
    )
    db.add(admin)
    db.commit()
    logger.info("Seeded initial admin user '%s'", username)
