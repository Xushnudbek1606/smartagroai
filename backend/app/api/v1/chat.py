from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.models import AgronomAssignment, Conversation, Message, Notification, User
from app.schemas import ChatMessageOut, ConversationCreate, ConversationOut, Page, UserOut
from app.services import subscription_service
from app.services.notifications import notify_new_message

router = APIRouter(prefix="/conversations", tags=["chat"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_participant(db, conversation: Conversation, user: User) -> User:
    """Return the *other* participant, enforcing access."""
    if user.role == "admin":
        if conversation.farmer_id == user.id:
            return db.get(User, conversation.agronomist_id)
        if conversation.agronomist_id == user.id:
            return db.get(User, conversation.farmer_id)
        raise forbidden("Not a participant", "not_participant")
    if user.id == conversation.farmer_id:
        partner = db.get(User, conversation.agronomist_id)
    elif user.id == conversation.agronomist_id:
        partner = db.get(User, conversation.farmer_id)
    else:
        raise forbidden("Not a participant", "not_participant")
    if partner is None:
        raise not_found("Partner not found")
    return partner


def _is_participant(conversation: Conversation, user: User) -> bool:
    if user.role == "admin":
        return True
    return user.id in (conversation.farmer_id, conversation.agronomist_id)


def _unread_count(db, conversation: Conversation, user: User) -> int:
    if user.id == conversation.farmer_id:
        since = conversation.farmer_last_read_at
    elif user.id == conversation.agronomist_id:
        since = conversation.agronom_last_read_at
    else:
        return 0
    q = db.query(Message).filter(
        Message.conversation_id == conversation.id, Message.sender_id != user.id
    )
    if since is not None:
        q = q.filter(Message.created_at > since)
    return q.count()


def _conversation_out(db, conversation: Conversation, user: User) -> ConversationOut:
    partner = get_participant(db, conversation, user)
    last = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .first()
    )
    preview = None
    if last:
        preview = (last.message_text or last.attachment_name or "")[:80]
    return ConversationOut(
        id=conversation.id,
        farmer_id=conversation.farmer_id,
        agronomist_id=conversation.agronomist_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        unread_count=_unread_count(db, conversation, user),
        partner=UserOut.model_validate(partner),
        last_message_preview=preview,
    )


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: DbSession, user: CurrentUser, unread_only: bool = False) -> list[ConversationOut]:
    q = db.query(Conversation)
    if user.role == "farmer":
        q = q.filter(Conversation.farmer_id == user.id)
    elif user.role == "agronom":
        q = q.filter(Conversation.agronomist_id == user.id)
    items = q.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc()).all()
    out = [_conversation_out(db, c, user) for c in items]
    if unread_only:
        out = [c for c in out if c.unread_count > 0]
    return out


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(body: ConversationCreate, db: DbSession, user: CurrentUser) -> ConversationOut:
    if user.role != "farmer":
        raise forbidden("Only farmers start conversations", "farmers_only")
    agronom = db.get(User, body.agronomist_id)
    if agronom is None or agronom.role != "agronom":
        raise not_found("Agronomist not found")
    if not agronom.is_active:
        raise bad_request("Agronomist is unavailable", "agronom_inactive")
    existing = (
        db.query(Conversation)
        .filter(
            Conversation.farmer_id == user.id,
            Conversation.agronomist_id == agronom.id,
        )
        .first()
    )
    if existing:
        # Reopening an existing conversation is free — only NEW conversations
        # consume the free advice quota.
        return _conversation_out(db, existing, user)
    subscription_service.check_advice_quota(db, user)
    conv = Conversation(farmer_id=user.id, agronomist_id=agronom.id)
    db.add(conv)
    subscription_service.record_advice_use(
        db, subscription_service.ensure_subscription(db, user)
    )
    db.commit()
    db.refresh(conv)
    return _conversation_out(db, conv, user)


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, db: DbSession, user: CurrentUser) -> ConversationOut:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("Conversation not found")
    return _conversation_out(db, conv, user)


@router.get("/{conversation_id}/messages", response_model=Page[ChatMessageOut])
def list_messages(
    conversation_id: str,
    db: DbSession,
    user: CurrentUser,
    before: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
) -> Page[ChatMessageOut]:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("Conversation not found")
    if not _is_participant(conv, user):
        raise forbidden("Not a participant", "not_participant")
    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    if before:
        q = q.filter(Message.created_at < before)
    total = (
        db.query(Message).filter(Message.conversation_id == conversation_id).count()
    )
    items = (
        q.order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    items.reverse()
    return Page[ChatMessageOut](
        items=[ChatMessageOut.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.post("/{conversation_id}/read", response_model=dict)
def mark_read(conversation_id: str, db: DbSession, user: CurrentUser) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise not_found("Conversation not found")
    if not _is_participant(conv, user):
        raise forbidden("Not a participant", "not_participant")
    now = _utcnow()
    if user.id == conv.farmer_id:
        conv.farmer_last_read_at = now
    elif user.id == conv.agronomist_id:
        conv.agronom_last_read_at = now
    db.add(conv)
    db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.sender_id != user.id,
        Message.read_at.is_(None),
    ).update({"read_at": now})
    db.commit()
    return {"status": "ok"}
