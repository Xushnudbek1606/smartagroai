from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.models import Conversation, Message, Notification, User

logger = logging.getLogger(__name__)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


class ChatConnectionManager:
    """Tracks live WebSocket connections per user and routes chat events."""

    def __init__(self) -> None:
        self._by_user: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._by_user[user_id].add(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        self._by_user[user_id].discard(ws)
        if not self._by_user[user_id]:
            self._by_user.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> int:
        dead: list[WebSocket] = []
        sent = 0
        for ws in list(self._by_user.get(user_id, ())):
            try:
                await ws.send_text(json.dumps(payload, default=str))
                sent += 1
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)
        return sent

    async def broadcast_new_message(self, db: Session, message: Message) -> None:
        conv = db.get(Conversation, message.conversation_id)
        if conv is None:
            return
        payload = {
            "event": "message.created",
            "conversation_id": conv.id,
            "message": {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "sender_id": message.sender_id,
                "message_text": message.message_text,
                "attachment_url": message.attachment_url,
                "attachment_name": message.attachment_name,
                "read_at": _iso(message.read_at),
                "created_at": _iso(message.created_at),
            },
        }
        for uid in (conv.farmer_id, conv.agronomist_id):
            await self.send_to_user(uid, payload)

    async def broadcast_read(self, conversation: Conversation, reader_id: str) -> None:
        payload = {
            "event": "message.read",
            "conversation_id": conversation.id,
            "reader_id": reader_id,
            "read_at": _iso(datetime.now(timezone.utc)),
        }
        for uid in (conversation.farmer_id, conversation.agronomist_id):
            await self.send_to_user(uid, payload)


chat_manager = ChatConnectionManager()
