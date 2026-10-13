from __future__ import annotations

import logging
from typing import Iterable

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TZ = "Asia/Tashkent"


def _api(method: str) -> str:
    s = get_settings()
    return f"{s.TELEGRAM_API_BASE}/bot{s.TELEGRAM_BOT_TOKEN}/{method}"


def send_message(
    chat_id: str | int,
    text: str,
    *,
    parse_mode: str | None = None,
    disable_web_page_preview: bool = True,
) -> bool:
    """Best-effort Telegram send. Returns True on success; never raises.

    The web platform must keep working when Telegram is down or unconfigured.
    """
    s = get_settings()
    if not s.telegram_configured:
        logger.info("Telegram not configured; skipping notification to %s", chat_id)
        return False
    try:
        payload: dict = {
            "chat_id": chat_id,
            "text": text[:4000],
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(_api("sendMessage"), json=payload)
            if resp.status_code != 200:
                logger.warning("Telegram sendMessage failed: status=%s", resp.status_code)
                return False
        return True
    except Exception as exc:  # network errors, timeouts...
        logger.warning("Telegram send_message error: %s", type(exc).__name__)
        return False


def send_messages(chat_ids: Iterable[str], text: str) -> int:
    return sum(1 for c in chat_ids if send_message(c, text))
