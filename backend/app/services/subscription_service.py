from __future__ import annotations

"""Subscription / usage quota service — role-based plans.

Each role gets its own default plan (farmer and agronom have different
limits: farmers get AI diagnoses, agronomists are staff and get generous
advice capacity but no AI diagnosis quota overhead). The defaults are
overridable per user in the subscriptions table; admins treat every
individual user's excess counters as records, not as billable work.

Free plan defaults by role:
  - farmer: 5 AI diagnoses + 5 agronomist advice conversations
  - agronom: unlimited advice (they answer) + generous diagnoses quota
    (verified agronomists may use the AI assistant themselves)
  - admin: never limited

Paid plans can be granted per user by an administrator (or a future
payment provider): a plan with paid_until in the future uses the paid
limits and counts from paid_used_* counters.

Counters are cumulative: deleting a diagnosis or a conversation does NOT
return the quota (see Subscription docstring). Admins are never limited.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, not_found
from app.models import Subscription, User
from app.schemas import SubscriptionOut

logger = logging.getLogger(__name__)

PAYWALL_STATUS_CODE = 402  # Payment Required
PAYWALL_CODE = "subscription_required"

PLAN_FREE = "free"
PLAN_PRO = "pro"

# ---------------------------------------------------------------------------
# Per-role default plans
# ---------------------------------------------------------------------------
# diagnoses_limit / advice_limit: -1 means "unlimited" for that feature.

PLAN_DEFAULTS: dict[str, dict[str, Any]] = {
    # Fermerlar: AI tashxis + agronom maslahati
    "farmer": {
        "plan": PLAN_FREE,
        "diagnoses_limit": 5,
        "advice_limit": 5,
    },
    # Agronomlar: maslahat berish cheklovsiz (ular ishlaydi), AI tashxis
    # ko'proq — bu fermerlarni ko'proq yordam beradi
    "agronom": {
        "plan": PLAN_FREE,
        "diagnoses_limit": 30,
        "advice_limit": -1,  # unlimited advice (they answer farmers)
    },
    # Adminlar umuman cheklovsiz (has_unlimited_usage)
    "admin": {
        "plan": PLAN_FREE,
        "diagnoses_limit": -1,
        "advice_limit": -1,
    },
}

# Paid "pro" plan limits per role — granted by admin (or payment provider).
# Provided as reference for admin tooling; actual grants write into the
# subscriptions row via update_subscription_admin.
PLAN_PRO_DEFAULTS: dict[str, dict[str, Any]] = {
    "farmer": {
        "diagnoses_limit": 50,
        "advice_limit": 30,
        "paid_until": None,  # configured when granting
    },
    "agronom": {
        "diagnoses_limit": -1,
        "advice_limit": -1,
        "paid_until": None,
    },
}

# What the /users/me/subscription endpoint exposes as "features" per role:
# farmers care about diagnosis + advice; agronomist mainly about advice.
_FEATURES_BY_ROLE: dict[str, tuple[str, ...]] = {
    "farmer": ("diagnoses", "advice"),
    "agronom": ("advice", "diagnoses"),
    "admin": ("diagnoses", "advice"),
}


def _is_unlimited(value: int) -> bool:
    return value is None or value < 0


def ensure_subscription(db: Session, user: User) -> Subscription:
    """Return the user's subscription, creating one with role-based defaults."""
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub is None:
        defaults = PLAN_DEFAULTS.get(user.role, PLAN_DEFAULTS["farmer"])
        sub = Subscription(
            user_id=user.id,
            plan=defaults["plan"],
            diagnoses_limit=defaults["diagnoses_limit"],
            advice_limit=defaults["advice_limit"],
        )
        db.add(sub)
        db.flush()
    return sub


def has_unlimited_usage(user: User) -> bool:
    """Admins (and users whose role default is -1 for a feature) are never
    limited by the paywall."""
    if user.role == "admin":
        return True
    defaults = PLAN_DEFAULTS.get(user.role, PLAN_DEFAULTS["farmer"])
    if defaults["diagnoses_limit"] == -1 and defaults["advice_limit"] == -1:
        return True
    return False


def _to_out(sub: Subscription, user: User) -> SubscriptionOut:
    unlimited_feature = {
        "diagnoses": _is_unlimited(sub.diagnoses_limit),
        "advice": _is_unlimited(sub.advice_limit),
    }
    out = {
        "plan": sub.plan,
        "role": user.role,
        "diagnoses_used": sub.diagnoses_used,
        "diagnoses_limit": sub.diagnoses_limit,
        "advice_used": sub.advice_used,
        "advice_limit": sub.advice_limit,
        "diagnoses_remaining": None if unlimited_feature["diagnoses"] else max(
            0, sub.diagnoses_limit - sub.diagnoses_used
        ),
        "advice_remaining": None if unlimited_feature["advice"] else max(
            0, sub.advice_limit - sub.advice_used
        ),
        "unlimited": has_unlimited_usage(user),
        "paid_until": sub.paid_until.isoformat() if sub.paid_until else None,
        "features": list(_FEATURES_BY_ROLE.get(user.role, ("diagnoses", "advice"))),
    }
    return SubscriptionOut(**out)


def get_subscription_out(db: Session, user: User) -> SubscriptionOut:
    if has_unlimited_usage(user):
        defaults = PLAN_DEFAULTS.get(user.role, PLAN_DEFAULTS["farmer"])
        return SubscriptionOut(
            plan=PLAN_FREE,
            role=user.role,
            diagnoses_used=0,
            diagnoses_limit=-1,
            advice_used=0,
            advice_limit=-1,
            diagnoses_remaining=None,
            advice_remaining=None,
            unlimited=True,
            paid_until=None,
            features=list(_FEATURES_BY_ROLE.get(user.role, ("diagnoses", "advice"))),
        )
    sub = ensure_subscription(db, user)
    return _to_out(sub, user)


def check_diagnosis_quota(db: Session, user: User) -> Subscription:
    """Raise 402 when the diagnosis quota is exhausted."""
    sub = ensure_subscription(db, user)
    if _is_unlimited(sub.diagnoses_limit) or has_unlimited_usage(user):
        return sub
    if sub.diagnoses_used >= sub.diagnoses_limit:
        raise AppError(
            PAYWALL_STATUS_CODE,
            PAYWALL_CODE,
            "Free diagnosis limit reached. Subscribe to continue.",
            {"limit": sub.diagnoses_limit, "feature": "diagnosis"},
        )
    return sub


def record_diagnosis_use(db: Session, sub: Subscription) -> None:
    sub.diagnoses_used += 1
    db.add(sub)


def check_advice_quota(db: Session, user: User) -> Subscription:
    """Raise 402 when the advice (conversation) quota is exhausted.

    Only *new* conversations count; chatting inside an existing one is free.
    Agronomists answer, so their default is unlimited.
    """
    sub = ensure_subscription(db, user)
    if _is_unlimited(sub.advice_limit) or has_unlimited_usage(user):
        return sub
    if sub.advice_used >= sub.advice_limit:
        raise AppError(
            PAYWALL_STATUS_CODE,
            PAYWALL_CODE,
            "Free agronomist advice limit reached. Subscribe to continue.",
            {"limit": sub.advice_limit, "feature": "advice"},
        )
    return sub


def record_advice_use(db: Session, sub: Subscription) -> None:
    sub.advice_used += 1
    db.add(sub)


# ---------------------------------------------------------------------------
# Admin management
# ---------------------------------------------------------------------------

FREE_PLAN_LIMITS_BY_ROLE = PLAN_DEFAULTS  # exported alias (free-plan defaults)


def get_user_subscription_admin(db: Session, user_id: str) -> dict[str, Any]:
    """Admin view: any user's subscription with effective limits."""
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User not found")
    sub = ensure_subscription(db, user)
    out = _to_out(sub, user)
    return out.model_dump()


def update_subscription_admin(
    db: Session,
    admin: User,
    user_id: str,
    *,
    plan: str | None = None,
    diagnoses_limit: int | None = None,
    advice_limit: int | None = None,
    paid_until: datetime | None = None,
    reset_usage: bool = False,
) -> SubscriptionOut:
    """Create/adjust a user's subscription. -1 limits mean unlimited."""
    user = db.get(User, user_id)
    if user is None:
        raise not_found("User not found")
    if user.role == "admin":
        raise bad_request("Admin accounts are always unlimited", "admin_unlimited")
    sub = ensure_subscription(db, user)
    if plan is not None:
        if plan not in (PLAN_FREE, PLAN_PRO):
            raise bad_request("plan must be 'free' or 'pro'", "invalid_plan")
        sub.plan = plan
    if diagnoses_limit is not None:
        if diagnoses_limit < -1:
            raise bad_request("diagnoses_limit must be >= -1", "invalid_limit")
        sub.diagnoses_limit = diagnoses_limit
    if advice_limit is not None:
        if advice_limit < -1:
            raise bad_request("advice_limit must be >= -1", "invalid_limit")
        sub.advice_limit = advice_limit
    if paid_until is not None:
        sub.paid_until = paid_until
    if reset_usage:
        sub.diagnoses_used = 0
        sub.advice_used = 0
    db.add(sub)
    db.flush()
    logger.info(
        "subscription updated: user=%s plan=%s diag=%s advice=%s paid_until=%s by=%s",
        user_id, sub.plan, sub.diagnoses_limit, sub.advice_limit,
        sub.paid_until, admin.id,
    )
    return _to_out(sub, user)
