from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class BotConfig:
    telegram_bot_token: str = field(default_factory=lambda: _env("TELEGRAM_BOT_TOKEN"))
    internal_api_url: str = field(
        default_factory=lambda: _env("BACKEND_INTERNAL_URL", "http://localhost:8000")
    )
    internal_secret: str = field(default_factory=lambda: _env("TELEGRAM_WEBHOOK_SECRET"))
    api_prefix: str = field(default_factory=lambda: _env("API_V1_PREFIX", "/api/v1"))

    @property
    def configured(self) -> bool:
        return bool(self.telegram_bot_token and self.internal_secret)


config = BotConfig()
