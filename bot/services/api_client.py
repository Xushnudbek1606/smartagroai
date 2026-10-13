from __future__ import annotations

import logging
from typing import Any

import httpx

from bot.config import config

logger = logging.getLogger(__name__)


class BackendError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _headers() -> dict[str, str]:
    return {"X-Internal-Secret": config.internal_secret}


def _url(path: str) -> str:
    return f"{config.internal_api_url.rstrip('/')}{config.api_prefix}{path}"


async def _post(path: str, json_body: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(_url(path), json=json_body, headers=_headers())
    return _handle(resp)


async def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(_url(path), params=params, headers=_headers())
    return _handle(resp)


def _handle(resp: httpx.Response) -> dict[str, Any]:
    if resp.status_code == 200:
        return resp.json()
    try:
        body = resp.json()
        detail = body.get("detail") or body.get("error", {}).get("message") or "error"
    except ValueError:
        detail = f"HTTP {resp.status_code}"
    code = {
        401: "invalid_invitation_code",
        404: "not_found",
        409: "telegram_already_linked",
        503: "backend_unavailable",
    }.get(resp.status_code, "backend_error")
    raise BackendError(code, detail)


async def claim_invitation(code: str, telegram_id: str, telegram_username: str | None) -> dict[str, Any]:
    """Exchange a one-time code for {username, temporary_password, language}."""
    return await _post(
        "/internal/telegram/claim",
        {
            "code": code,
            "telegram_id": str(telegram_id),
            "telegram_username": telegram_username,
        },
    )


async def account_status(telegram_id: str) -> dict[str, Any]:
    return await _get("/internal/telegram/status", {"telegram_id": str(telegram_id)})


async def user_info(telegram_id: str) -> dict[str, Any]:
    return await _get("/internal/telegram/user", {"telegram_id": str(telegram_id)})


async def set_preferences(telegram_id: str, enabled: bool) -> dict[str, Any]:
    return await _post(
        "/internal/telegram/preferences",
        {"telegram_id": str(telegram_id), "enabled": enabled},
    )


async def weather(location: str) -> dict[str, Any]:
    return await _get("/internal/telegram/weather", {"location": location})


async def heartbeat(version: str = "1.0.0") -> None:
    try:
        await _post("/internal/telegram/heartbeat", {"version": version})
    except Exception as exc:  # heartbeat must never break the bot
        logger.warning("heartbeat failed: %s", type(exc).__name__)
