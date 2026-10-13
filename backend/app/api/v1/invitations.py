from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_roles
from app.core.errors import forbidden, not_found
from app.models import Invitation, User
from app.schemas import (
    InvitationClaimOut,
    InvitationClaimRequest,
    InvitationCreate,
    InvitationCreateOut,
    InvitationOut,
    InvitationStatusOut,
)
from app.services import invitation_service

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("", response_model=InvitationCreateOut, status_code=201)
def create_invitation(
    body: InvitationCreate,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> InvitationCreateOut:
    target = db.get(User, body.user_id)
    if target is None:
        raise not_found("User not found")
    result = invitation_service.create_invitation(
        db, user_id=body.user_id, created_by=admin.id, purpose=body.purpose
    )
    db.commit()
    db.refresh(result["invitation"])
    return InvitationCreateOut(
        invitation=InvitationOut.model_validate(result["invitation"]),
        code=result["code"],
    )


@router.get("/mine", response_model=InvitationOut | None)
def my_invitation(db: DbSession, user_id: str, _: User = Depends(require_roles("admin"))):
    inv = (
        db.query(Invitation)
        .filter(Invitation.user_id == user_id, Invitation.used_at.is_(None))
        .order_by(Invitation.created_at.desc())
        .first()
    )
    return InvitationOut.model_validate(inv) if inv else None


@router.post("/claim", response_model=InvitationClaimOut)
def claim(body: InvitationClaimRequest, db: DbSession) -> InvitationClaimOut:
    """Called by the Telegram bot through the internal API (protected by
    TELEGRAM_WEBHOOK_SECRET at the router level), never by the public web app."""
    result = invitation_service.claim_invitation(
        db, code=body.code, telegram_id=body.telegram_id, telegram_username=body.telegram_username
    )
    return InvitationClaimOut(**result)


@router.get("/status", response_model=InvitationStatusOut)
def invitation_status(telegram_id: str, db: DbSession) -> InvitationStatusOut:
    return InvitationStatusOut(**invitation_service.invitation_status(db, telegram_id=telegram_id))
