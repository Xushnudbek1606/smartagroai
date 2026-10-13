from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status

from app.core.deps import (
    CurrentUser,
    DbSession,
    FreshUser,
    audit,
    rate_limiter,
    require_roles,
)
from app.core.errors import bad_request, conflict, not_found
from app.core.security import generate_temp_password, hash_password
from app.models import AgronomistProfile, User
from app.repositories import users as users_repo
from app.schemas import (
    AdminUserUpdate,
    InvitationCreateOut,
    MessageOut,
    SubscriptionAdminOut,
    SubscriptionAdminUpdate,
    SubscriptionOut,
    Page,
    PasswordResetOut,
    UserCreate,
    UserCreateOut,
    UserOut,
    UserUpdate,
)
from app.services import auth_service, files, invitation_service, subscription_service
from app.services.notifications import notify_security

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/subscription", response_model=SubscriptionOut)
def get_my_subscription(user: CurrentUser, db: DbSession) -> SubscriptionOut:
    """Current plan and remaining quota — role-based (farmer/agronom differ)."""
    return subscription_service.get_subscription_out(db, user)


@router.get("/{user_id}/subscription", response_model=SubscriptionAdminOut)
def get_user_subscription_admin(
    user_id: str,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> SubscriptionAdminOut:
    """Admin: inspect any user's subscription (role-based plan)."""
    target = db.get(User, user_id)
    if target is None:
        raise not_found("User not found")
    data = subscription_service.get_user_subscription_admin(db, user_id)
    data["user_id"] = user_id
    data["username"] = target.username
    return SubscriptionAdminOut(**data)


@router.patch("/{user_id}/subscription", response_model=SubscriptionAdminOut)
def update_user_subscription_admin(
    user_id: str,
    body: SubscriptionAdminUpdate,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> SubscriptionAdminOut:
    """Admin: grant a role-appropriate plan/limits or a paid extension.

    Limits: -1 = unlimited. reset_usage zeroes counters (e.g. after renewal).
    """
    sub = subscription_service.update_subscription_admin(
        db,
        admin,
        user_id,
        plan=body.plan,
        diagnoses_limit=body.diagnoses_limit,
        advice_limit=body.advice_limit,
        paid_until=body.paid_until,
        reset_usage=body.reset_usage,
    )
    target = db.get(User, user_id)
    audit(
        db,
        admin.id,
        "admin.subscription_updated",
        entity_type="subscription",
        entity_id=user_id,
        detail={
            "role": target.role,
            "plan": sub.plan,
            "diagnoses_limit": sub.diagnoses_limit,
            "advice_limit": sub.advice_limit,
            "reset_usage": body.reset_usage,
        },
    )
    db.commit()
    data = sub.model_dump()
    data["user_id"] = user_id
    data["username"] = target.username
    return SubscriptionAdminOut(**data)


@router.get("/me", response_model=UserOut)
def get_me(user: FreshUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    db.add(user)
    audit(db, user.id, "user.profile_updated", entity_type="user", entity_id=user.id)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> UserOut:
    rate_limiter.check(f"upload:{user.id}", 20, 60)
    data = await file.read()
    try:
        url = files.save_avatar(data)
    except files.FileValidationError as exc:
        raise bad_request(exc.message, exc.code)
    user.avatar_url = url
    db.add(user)
    audit(db, user.id, "user.avatar_updated", entity_type="user", entity_id=user.id)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("", response_model=Page[UserOut])
def list_users(
    db: DbSession,
    _: User = Depends(require_roles("admin")),  # noqa: ARG001
    role: str | None = Query(default=None, pattern=r"^(admin|farmer|agronom)$"),
    search: str | None = Query(default=None, max_length=120),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[UserOut]:
    items, total = users_repo.list_users(
        db,
        role=role,
        search=search,
        is_active=is_active,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return Page[UserOut](
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.post("", response_model=UserCreateOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> UserCreateOut:
    if users_repo.get_by_username(db, body.username):
        raise conflict("Username already exists", "username_taken")
    settings_user = User(
        full_name=body.full_name.strip(),
        username=body.username.strip(),
        password_hash=hash_password(generate_temp_password()),
        role=body.role,
        phone=body.phone,
        region=body.region,
        district=body.district,
        preferred_language=body.preferred_language,
        is_active=True,
        must_change_password=True,
    )
    db.add(settings_user)
    db.flush()
    if body.role == "agronom":
        db.add(AgronomistProfile(user_id=settings_user.id))
    invitation = invitation_service.create_invitation(
        db, user_id=settings_user.id, created_by=admin.id, purpose="telegram_link"
    )
    audit(
        db,
        admin.id,
        "admin.user_created",
        entity_type="user",
        entity_id=settings_user.id,
        detail={"role": body.role, "username": body.username},
    )
    db.commit()
    db.refresh(settings_user)
    return UserCreateOut(
        user=UserOut.model_validate(settings_user),
        invitation_code=invitation["code"],
        invitation_expires_at=invitation["expires_at"],
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    body: AdminUserUpdate,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> UserOut:
    target = db.get(User, user_id)
    if target is None:
        raise not_found("User not found")
    data = body.model_dump(exclude_unset=True)
    if "role" in data and data["role"] != target.role and target.id == admin.id:
        raise bad_request("You cannot change your own role", "own_role")
    for field, value in data.items():
        setattr(target, field, value)
    db.add(target)
    audit(db, admin.id, "admin.user_updated", entity_type="user", entity_id=user_id, detail=data)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: str,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> UserOut:
    target = db.get(User, user_id)
    if target is None:
        raise not_found("User not found")
    if target.id == admin.id:
        raise bad_request("You cannot deactivate your own account", "self_deactivate")
    target.is_active = False
    db.add(target)
    auth_service.revoke_all_for_user(db, user_id)
    audit(db, admin.id, "admin.user_deactivated", entity_type="user", entity_id=user_id)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: str,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> UserOut:
    target = db.get(User, user_id)
    if target is None:
        raise not_found("User not found")
    target.is_active = True
    db.add(target)
    audit(db, admin.id, "admin.user_activated", entity_type="user", entity_id=user_id)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/{user_id}/temporary-password", response_model=PasswordResetOut)
def regenerate_temporary_password(
    user_id: str,
    db: DbSession,
    admin: User = Depends(require_roles("admin")),
) -> PasswordResetOut:
    """Generate a new one-time password (returned once). Use the Telegram
    invitation flow instead when possible — it delivers the credentials
    directly into the owner's private chat."""
    target = db.get(User, user_id)
    if target is None:
        raise not_found("User not found")
    temp = generate_temp_password()
    target.password_hash = hash_password(temp)
    target.must_change_password = True
    db.add(target)
    auth_service.revoke_all_for_user(db, user_id)
    audit(db, admin.id, "admin.temp_password_regenerated", entity_type="user", entity_id=user_id)
    db.commit()
    notify_security(
        target,
        {
            "uz-Latn": "Parolingiz administrator tomonidan yangilandi. Iltimos, yangi parol bilan kiring.",
            "uz-Cyrl": "Паролингиз администратор томонидан янгиланди. Янги парол билан киринг.",
            "en": "Your password was reset by an administrator. Please sign in with the new password.",
            "ru": "Ваш пароль был сброшен администратором. Войдите с новым паролем.",
        },
    )
    return PasswordResetOut(username=target.username, temporary_password=temp)
