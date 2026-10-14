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

# every handler below answers ONLY in private chats — group members never
# see farm data, weather for other people's regions, or invitation codes
PRIVATE_ONLY_TEXTS = {
    "uz-Latn": "🛡 Bu buyruq faqat shaxsiy (private) suhbatda ishlaydi.",
    "uz-Cyrl": "🛡 Бу буйруқ фақат шахсий (private) сӯҳбатда ишлайди.",
    "en": "🛡 This command works only in a private chat.",
    "ru": "🛡 Эта команда работает только в личном чате.",
}

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


async def _lang_of(telegram_id: int, telegram_username: str | None = None) -> str:
    """Language of the private profile; also refreshes the stored @username
    so the platform binding never goes stale."""
    try:
        info = await api_client.user_info(telegram_id, telegram_username)
        return info.get("language") or "uz-Latn"
    except Exception:
        return "uz-Latn"


def _guard_private(message: Message) -> str | None:
    """Return the private-only notice text when the chat is not private."""
    if message.chat.type != "private":
        return PRIVATE_ONLY_TEXTS["uz-Latn"]
    return None


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
    lang = await _lang_of(message.from_user.id, message.from_user.username)
    await message.answer(tr(lang, "welcome"))


@router.message(Command("help", "yardam"))
async def cmd_help(message: Message) -> None:
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
    lang = await _lang_of(message.from_user.id, message.from_user.username)
    await message.answer(tr(lang, "help"))


@router.message(Command("account"))
async def cmd_account(message: Message) -> None:
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
    tg_id = message.from_user.id
    try:
        status = await api_client.account_status(tg_id)
    except BackendError as exc:
        logger.warning("account status failed: %s", exc.code)
        status = {"linked": False}

    lang = await _lang_of(tg_id, message.from_user.username)
    if not status.get("linked"):
        await message.answer(tr(lang, "account_not_linked"))
        return

    # already linked — a new code is not accepted for security reasons, and the
    # profile is shown only here, in the owner's private chat
    try:
        info = await api_client.user_info(tg_id, message.from_user.username)
    except Exception:
        info = {}
    await message.answer(
        tr(lang, "account_linked").format(
            username=status.get('username', '—'), password='••••••'
        )
    )
    if info.get("found"):
        await message.answer(
            tr(lang, "profile_info").format(
                full_name=info.get("full_name") or "—",
                role=info.get("role") or "—",
                region=info.get("district") or info.get("region") or "—",
                telegram_username=(
                    f"@{info['telegram_username']}" if info.get("telegram_username") else "—"
                ),
            )
        )


@router.message(F.text.regexp(r"(?i)^/account\s+[A-Za-z0-9]{4,16}$"))
async def cmd_account_with_code(message: Message) -> None:
    """User sends /account CODE — exchange for credentials."""
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
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
        lang = await _lang_of(tg.id, tg.username)
        key = (
            "code_invalid"
            if exc.code in ("invalid_invitation_code", "invitation_expired")
            else (
                "already_linked"
                if exc.code == "telegram_already_linked"
                else "username_mismatch" if exc.code == "telegram_username_mismatch" else "error"
            )
        )
        await message.answer(tr(lang, key))
        return

    lang = result.get("language") or "uz-Latn"
    await message.answer(
        tr(lang, "account_linked").format(
            username=result["username"], password=result["temporary_password"]
        )
    )


@router.message(Command("weather"))
async def cmd_weather(message: Message) -> None:
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
    tg_id = message.from_user.id
    lang = await _lang_of(tg_id, message.from_user.username)
    # /weather is for LINKED users only — an anonymous stranger in some other
    # chat must not be able to pull platform weather data
    try:
        info = await api_client.user_info(tg_id, message.from_user.username)
    except Exception:
        info = {"found": False}
    if not info.get("found"):
        await message.answer(tr(lang, "account_not_linked"))
        return
    # default = the caller's OWN region/district, so a farmer sees the weather
    # for their farm and not somebody else's area
    args = (message.text or "").split(maxsplit=1)
    if len(args) > 1:
        location = args[1].strip()
    else:
        location = (info.get("district") or info.get("region") or "").strip()
    if not location:
        await message.answer(tr(lang, "weather_prompt"))
        return
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
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
    lang = await _lang_of(message.from_user.id, message.from_user.username)
    await message.answer(tr(lang, "language_prompt"), reply_markup=_lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def on_lang_choice(call: CallbackQuery) -> None:
    code = (call.data or "").split(":", 1)[1]
    if code == "menu":
        lang = await _lang_of(call.from_user.id, call.from_user.username)
        await call.message.edit_text(tr(lang, "language_prompt"), reply_markup=_lang_kb())
        await call.answer()
        return
    if code not in SUPPORTED:
        await call.answer()
        return
    # persist the choice to the platform profile so web + notifications
    # follow the same language
    try:
        await api_client.set_language(str(call.from_user.id), code)
    except Exception:
        logger.warning("set_language failed for language=%s", code)
    await call.message.edit_text(tr(code, "language_set", language=LANG_NAMES[code]))
    await call.answer()


@router.message(Command("notifications"))
async def cmd_notifications(message: Message) -> None:
    guard = _guard_private(message)
    if guard:
        await message.answer(guard)
        return
    lang = await _lang_of(message.from_user.id, message.from_user.username)
    try:
        info = await api_client.user_info(message.from_user.id, message.from_user.username)
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
