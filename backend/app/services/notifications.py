from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.models import User

from .telegram_service import send_message

logger = logging.getLogger(__name__)


def _enabled(user: User) -> bool:
    return bool(user.telegram_id) and user.telegram_notifications_enabled


def notify_user(user: User, title: str, body: str) -> None:
    """Send a Telegram notification for an in-app notification (best effort)."""
    if not _enabled(user):
        return
    text = f"*{_escape(title)}*\n{_escape(body)}" if body else _escape(title)
    send_message(user.telegram_id, text, parse_mode="Markdown")  # type: ignore[arg-type]


def notify_new_message(user: User, sender_name: str, preview: str) -> None:
    if not _enabled(user):
        return
    text = f"💬 *{_escape(sender_name)}*\n{_escape(preview[:200])}"
    send_message(user.telegram_id, text, parse_mode="Markdown")  # type: ignore[arg-type]


def notify_diagnosis_done(user: User, disease_name: str | None, confidence: float | None) -> None:
    if not _enabled(user):
        return
    disease = disease_name or "—"
    conf = f"{confidence * 100:.0f}%" if confidence is not None else "—"
    text = (
        "🔬 *AI tahlil yakunlandi*\n"
        f"Kasallik: {_escape(disease)}\nIshonchlilik: {conf}\n"
        "Platformadagi «AI tashxis» bo'limida batafsil ko'ring."
    )
    send_message(user.telegram_id, text, parse_mode="Markdown")  # type: ignore[arg-type]


def notify_security(user: User, text_by_lang: dict[str, str]) -> None:
    if not _enabled(user):
        return
    text = text_by_lang.get(user.preferred_language, text_by_lang.get("uz-Latn", ""))
    send_message(user.telegram_id, _escape(text))  # type: ignore[arg-type]


def _escape(text: str) -> str:
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text
