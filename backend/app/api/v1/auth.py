from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, audit, client_ip, rate_limiter
from app.core.errors import unauthorized
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageOut,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, request: Request, db: DbSession) -> TokenPair:
    settings = get_settings()
    key = f"login:{client_ip(request)}:{body.username.lower()}"
    rate_limiter.check(key, settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    try:
        user = auth_service.authenticate(db, body.username.strip(), body.password)
    except Exception:
        audit(db, None, "auth.login_failed", detail={"username": body.username, "ip": client_ip(request)})
        db.commit()
        raise
    audit(db, user.id, "auth.login", detail={"ip": client_ip(request)})
    tokens = auth_service.issue_tokens(db, user)
    rate_limiter.reset(key)
    return TokenPair(**tokens)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: DbSession) -> TokenPair:
    return TokenPair(**auth_service.rotate_refresh_token(db, body.refresh_token))


@router.post("/logout", response_model=MessageOut)
def logout(body: RefreshRequest, db: DbSession) -> MessageOut:
    auth_service.revoke_refresh_token(db, body.refresh_token)
    return MessageOut(detail="Logged out")


@router.post("/change-password", response_model=MessageOut)
def change_password(body: ChangePasswordRequest, user: CurrentUser, db: DbSession) -> MessageOut:
    auth_service.change_password(db, user, body.current_password, body.new_password)
    audit(db, user.id, "auth.password_changed", entity_type="user", entity_id=user.id)
    return MessageOut(detail="Password changed successfully")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
