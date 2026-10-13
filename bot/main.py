from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.handlers import commands
from bot.services import api_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 120  # seconds


async def heartbeat_loop(bot: Bot) -> None:
    """Tell the backend we are alive so /admin/system-health stays accurate."""
    while True:
        try:
            await api_client.heartbeat()
        except Exception as exc:
            logger.warning("heartbeat error: %s", type(exc).__name__)
        await asyncio.sleep(HEARTBEAT_INTERVAL)


async def main() -> None:
    if not config.configured:
        logger.error(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_WEBHOOK_SECRET are not set. "
            "The bot cannot start; the web platform keeps working without it."
        )
        return

    bot = Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(commands.router)

    logger.info("SmartAgroAI bot starting (polling)")
    asyncio.create_task(heartbeat_loop(bot))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
