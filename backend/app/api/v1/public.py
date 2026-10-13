from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.deps import DbSession
from app.models import Setting

router = APIRouter(prefix="/public", tags=["public"])

# Only these setting keys are safe to expose without authentication.
# Admins edit them under Admin → Settings; the public landing page reads them.
PUBLIC_SETTING_KEYS: tuple[str, ...] = ("landing_banner", "contact")


@router.get("/settings")
def public_settings(db: DbSession) -> dict[str, dict[str, Any]]:
    rows = db.query(Setting).filter(Setting.key.in_(PUBLIC_SETTING_KEYS)).all()
    stored: dict[str, Any] = {
        r.key: r.value for r in rows if isinstance(r.value, dict)
    }
    return {"settings": {key: stored.get(key, {}) for key in PUBLIC_SETTING_KEYS}}
