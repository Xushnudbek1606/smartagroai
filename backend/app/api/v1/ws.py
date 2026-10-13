from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Conversation, Message, Notification, User
from app.services import files as files_service
from app.websockets.chat_manager import chat_manager

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_MESSAGE_LENGTH = 4000
MAX_CHAT_IMAGE_BYTES = 6 * 1024 * 1024  # base64-decoded image size cap
 

def _save_chat_image(data: bytes) -> tuple[str, str] | None:
    """Validate (magic bytes) and persist a chat image. Returns (url, name)."""
    detected = files_service.detect_image_type(data[:64])
    if detected is None:
        return None
    if len(data) > MAX_CHAT_IMAGE_BYTES:
        return None
    from app.core.config import get_settings

    settings = get_settings()
    import secrets

    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[detected]
    name = secrets.token_urlsafe(16).replace("-", "a").replace("_", "b") + ext
    subdir = settings.upload_dir / "chat_images"
    subdir.mkdir(parents=True, exist_ok=True)
    (subdir / name).write_bytes(data)
    return f"/static/chat_images/{name}", name


def _auth_user(token: str) -> User | None:
    try:
        payload = decode_token(token, expected_type="access")
    except Exception:
        return None
    db: Session = SessionLocal()
    try:
        user = db.get(User, payload.get("sub"))
        if user is None or not user.is_active:
            return None
        db.expunge(user)
        return user
    finally:
        db.close()


def _participant(db: Session, conversation: Conversation, user: User) -> bool:
    if user.role == "admin":
        return True
    return user.id in (conversation.farmer_id, conversation.agronomist_id)


@router.websocket("/ws/chat/{conversation_id}")
async def chat_socket(websocket: WebSocket, conversation_id: str, token: str = "") -> None:
    user = _auth_user(token) if token else None
    if user is None:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None or not _participant(db, conversation, user):
            await websocket.close(code=4403)
            return
        await chat_manager.connect(user.id, websocket)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event = data.get("event")
                if event == "message.send":
                    text = (data.get("text") or "").strip()
                    if not text:
                        continue
                    if len(text) > MAX_MESSAGE_LENGTH:
                        await websocket.send_text(
                            json.dumps({"event": "error", "code": "message_too_long"})
                        )
                        continue
                    message = Message(
                        conversation_id=conversation.id,
                        sender_id=user.id,
                        message_text=text[:MAX_MESSAGE_LENGTH],
                    )
                    db.add(message)
                    conversation.last_message_at = datetime.now(timezone.utc)
                    db.add(conversation)
                    # store an in-app notification for the partner
                    partner_id = (
                        conversation.agronomist_id
                        if user.id == conversation.farmer_id
                        else conversation.farmer_id
                    )
                    db.add(
                        Notification(
                            user_id=partner_id,
                            title=f"Yangi xabar: {user.full_name}",
                            body=text[:200],
                            type="chat",
                            link=f"/chat/{conversation.id}",
                        )
                    )
                    db.commit()
                    db.refresh(message)
                    await chat_manager.broadcast_new_message(db, message)
                elif event == "message.send_image":
                    # Both farmer and agronom may send images within their own chat.
                    image_url, image_name = None, None
                    payload = data.get("image") or ""
                    decoded = None
                    if payload.startswith("data:image/") and ";base64," in payload:
                        import base64

                        try:
                            decoded = base64.b64decode(payload.split(";base64,", 1)[1], validate=True)
                        except Exception:
                            decoded = None
                    if decoded:
                        saved = _save_chat_image(decoded)
                        if saved:
                            image_url, image_name = saved
                    if not image_url:
                        await websocket.send_text(
                            json.dumps({"event": "error", "code": "invalid_image"})
                        )
                        continue
                    note = (data.get("text") or "").strip()[:MAX_MESSAGE_LENGTH]
                    message = Message(
                        conversation_id=conversation.id,
                        sender_id=user.id,
                        message_text=note or None,
                        attachment_url=image_url,
                        attachment_name=image_name,
                    )
                    db.add(message)
                    conversation.last_message_at = datetime.now(timezone.utc)
                    db.add(conversation)
                    partner_id = (
                        conversation.agronomist_id
                        if user.id == conversation.farmer_id
                        else conversation.farmer_id
                    )
                    db.add(
                        Notification(
                            user_id=partner_id,
                            title=f"Yangi rasm: {user.full_name}",
                            body=note[:200] or "📷 Rasm yuborildi",
                            type="chat",
                            link=f"/chat/{conversation.id}",
                        )
                    )
                    db.commit()
                    db.refresh(message)
                    await chat_manager.broadcast_new_message(db, message)
                elif event == "message.read":
                    now = datetime.now(timezone.utc)
                    if user.id == conversation.farmer_id:
                        conversation.farmer_last_read_at = now
                    elif user.id == conversation.agronomist_id:
                        conversation.agronom_last_read_at = now
                    db.add(conversation)
                    db.query(Message).filter(
                        Message.conversation_id == conversation.id,
                        Message.sender_id != user.id,
                        Message.read_at.is_(None),
                    ).update({"read_at": now})
                    db.commit()
                    await chat_manager.broadcast_read(conversation, user.id)
                elif event == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WebSocket error")
        finally:
            chat_manager.disconnect(user.id, websocket)
    finally:
        db.close()
