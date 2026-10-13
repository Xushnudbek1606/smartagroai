from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.locales import SUPPORTED, tr
from bot.services import api_client
from bot.services.api_client import BackendError

logger = logging.getLogger(__name__)

router = Router(name="commands")

# /account CODE — single-use invitation code
_CODE_RE = re.compile(r"^[A-Za-z0-9]{4,16}$")

LANG_NAMES = {
    "uz-Latn": "O'zbekcha (Lotin)",
    "uz-Cyrl": "Ўзбекча (Кирилл)",
    "en": "English",
    "ru": "Русский",
}


def _lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LANG_NAMES[code], callback_data=f"lang:{code}")]
            for code in SUPPORTED
        ]
    )


def _notif_kb(enabled: bool) -> InlineKeyboardMarkup:
    lang_row = InlineKeyboardButton(text="🌐 Language", callback_data="lang:menu")
    if enabled:
        notif = InlineKeyboardButton(text="🔇 Off", callback_data="notif:off")
    else:
        notif = InlineKeyboardButton(text="🔔 On", callback_data="notif:on")
    return InlineKeyboardMarkup(inline_keyboard=[[notif], [lang_row]])


async def _lang_of(telegram_id: int) -> str:
    try:
        info = await api_client.user_info(telegram_id)
        return info.get("language") or "uz-Latn"
    except Exception:
        return "uz-Latn"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    lang = await _lang_of(message.from_user.id)
    await message.answer(tr(lang, "welcome"))


@router.message(Command("help", "yardam"))
async def cmd_help(message: Message) -> None:
    lang = await _lang_of(message.from_user.id)
    await message.answer(tr(lang, "help"))


@router.message(Command("account"))
async def cmd_account(message: Message) -> None:
    tg_id = message.from_user.id
    try:
        status = await api_client.account_status(tg_id)
    except BackendError as exc:
        logger.warning("account status failed: %s", exc.code)
        status = {"linked": False}

    lang = await _lang_of(tg_id)
    if not status.get("linked"):
        await message.answer(tr(lang, "account_not_linked"))
        return

    # already linked — a new code is not accepted for security reasons
    await message.answer(
        tr(lang, "account_linked").format(
            username=status.get('username', '—'), password='••••••'
        )
    )


@router.message(F.text.regexp(r"(?i)^/account\s+[A-Za-z0-9]{4,16}$"))
async def cmd_account_with_code(message: Message) -> None:
    """User sends /account CODE — exchange for credentials."""
    tg = message.from_user
    match = re.match(r"(?i)^/account\s+([A-Za-z0-9]{4,16})$", (message.text or "").strip())
    if match is None:
        return
    code = match.group(1).upper()

    # check existing link first
    try:
        status = await api_client.account_status(tg.id)
        if status.get("linked"):
            lang = status.get("language") or "uz-Latn"
            await message.answer(tr(lang, "already_linked"))
            return
    except BackendError:
        pass

    try:
        result = await api_client.claim_invitation(code, str(tg.id), tg.username)
    except BackendError as exc:
        lang = await _lang_of(tg.id)
        key = "code_invalid" if exc.code in ("invalid_invitation_code", "invitation_expired") else (
            "already_linked" if exc.code == "telegram_already_linked" else "error"
        )
        await message.answer(tr(lang, key))
        return

    lang = result.get("language") or "uz-Latn"
    # credentials go ONLY to the private chat of the verified Telegram user
    if message.chat.type != "private":
        await message.answer(tr(lang, "error"))
        return
    await message.answer(
        tr(lang, "account_linked").format(
            username=result["username"], password=result["temporary_password"]
        )
    )


@router.message(Command("weather"))
async def cmd_weather(message: Message) -> None:
    lang = await _lang_of(message.from_user.id)
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer(tr(lang, "weather_prompt"))
        return
    location = args[1].strip()
    try:
        data = await api_client.weather(location)
    except BackendError as exc:
        await message.answer(tr(lang, "weather_error", message=exc.message))
        return
    if "error" in data:
        await message.answer(tr(lang, "weather_error", message=data["error"]["message"]))
        return
    await message.answer(
        tr(lang, "weather_current").format(
            location=data.get("location", location),
            temperature=data.get("temperature", "?"),
            feels_like=data.get("feels_like", "?"),
            humidity=data.get("humidity", "?"),
            wind_speed=data.get("wind_speed", "?"),
            description=data.get("description", ""),
            fetched_at=str(data.get("fetched_at", ""))[:16].replace("T", " "),
        )
    )


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    lang = await _lang_of(message.from_user.id)
    await message.answer(tr(lang, "language_prompt"), reply_markup=_lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def on_lang_choice(call: CallbackQuery) -> None:
    code = (call.data or "").split(":", 1)[1]
    if code == "menu":
        lang = await _lang_of(call.from_user.id)
        await call.message.edit_text(tr(lang, "language_prompt"), reply_markup=_lang_kb())
        await call.answer()
        return
    if code not in SUPPORTED:
        await call.answer()
        return
    # the bot language follows the platform profile language; without a linked
    # account we can only acknowledge the choice locally
    try:
        await api_client.user_info(call.from_user.id)
    except Exception:
        pass
    await call.message.edit_text(tr(code, "language_set", language=LANG_NAMES[code]))
    await call.answer()


@router.message(Command("notifications"))
async def cmd_notifications(message: Message) -> None:
    lang = await _lang_of(message.from_user.id)
    try:
        info = await api_client.user_info(message.from_user.id)
    except Exception:
        info = {"found": False}
    if not info.get("found"):
        await message.answer(tr(lang, "account_not_linked"))
        return
    enabled = bool(info.get("notifications_enabled", True))
    await message.answer("🔔", reply_markup=_notif_kb(enabled))


@router.callback_query(F.data.startswith("notif:"))
async def on_notif_toggle(call: CallbackQuery) -> None:
    enable = (call.data or "").endswith("on")
    lang = await _lang_of(call.from_user.id)
    try:
        await api_client.set_preferences(str(call.from_user.id), enable)
    except Exception:
        await call.answer(tr(lang, "error"), show_alert=True)
        return
    await call.message.edit_text(
        tr(lang, "notifications_on" if enable else "notifications_off"),
        reply_markup=_notif_kb(enable),
    )
    await call.answer()
