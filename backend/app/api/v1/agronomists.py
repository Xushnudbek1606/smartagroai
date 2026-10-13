from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.deps import CurrentUser, DbSession, audit, require_roles  # noqa: F401
from app.core.errors import bad_request, forbidden, not_found
from app.models import AgronomAssignment, User
from app.schemas import Page, UserOut

router = APIRouter(prefix="/agronomists", tags=["agronomists"])


@router.get("", response_model=Page[UserOut])
def list_agronomists(
    db: DbSession,
    _: User = Depends(require_roles("farmer", "admin")),
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[UserOut]:
    q = db.query(User).filter(User.role == "agronom", User.is_active.is_(True))
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(User.full_name.ilike(like) | User.region.ilike(like))
    total = q.count()
    items = q.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size).all()
    return Page[UserOut](
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/assigned", response_model=Page[UserOut])
def assigned_farmers(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[UserOut]:
    """Farmers explicitly assigned to the current agronom."""
    if user.role == "admin":
        q = db.query(User).filter(User.role == "farmer", User.is_active.is_(True))
    else:
        q = (
            db.query(User)
            .join(AgronomAssignment, AgronomAssignment.farmer_id == User.id)
            .filter(AgronomAssignment.agronomist_id == user.id)
        )
    total = q.count()
    items = q.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size).all()
    return Page[UserOut](
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


class AssignmentIn(BaseModel):
    agronomist_id: str | None = None


@router.post("/assign/{farmer_id}", response_model=dict)
def assign_farmer(
    farmer_id: str,
    db: DbSession,
    user: CurrentUser,
    body: AssignmentIn | None = None,
) -> dict:
    """Admin links a farmer to an agronom; an agronom may link to self."""
    if user.role == "admin":
        if body is None or not body.agronomist_id:
            raise bad_request("agronomist_id is required", "missing_agronomist")
        agronom_id = body.agronomist_id
    elif user.role == "agronom":
        agronom_id = user.id
    else:
        raise forbidden("Only admins and agronomists can assign farmers", "insufficient_role")

    farmer = db.get(User, farmer_id)
    if farmer is None or farmer.role != "farmer":
        raise not_found("Farmer not found")
    agronom = db.get(User, agronom_id)
    if agronom is None or agronom.role != "agronom":
        raise not_found("Agronomist not found")

    existing = (
        db.query(AgronomAssignment)
        .filter(
            AgronomAssignment.farmer_id == farmer_id,
            AgronomAssignment.agronomist_id == agronom_id,
        )
        .first()
    )
    if existing is None:
        db.add(AgronomAssignment(farmer_id=farmer_id, agronomist_id=agronom_id))
        audit(
            db,
            user.id,
            "agronomist.assigned",
            entity_type="user",
            entity_id=farmer_id,
            detail={"agronomist_id": agronom_id},
        )
        db.commit()
    return {"status": "ok", "agronomist_id": agronom_id, "farmer_id": farmer_id}
