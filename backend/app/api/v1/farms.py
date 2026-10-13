from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import forbidden, not_found
from app.models import Crop, Farm, User
from app.schemas import CropOut, FarmCreate, FarmOut, FarmUpdate, Page

router = APIRouter(prefix="/farms", tags=["farms"])


def _can_access(user: User, farm: Farm) -> bool:
    return user.role == "admin" or farm.owner_id == user.id


def _farm_out(farm: Farm) -> FarmOut:
    out = FarmOut.model_validate(farm)
    out.crops_count = len(farm.crops)
    return out


@router.get("", response_model=Page[FarmOut])
def list_farms(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    owner_id: str | None = Query(default=None),
) -> Page[FarmOut]:
    q = db.query(Farm)
    if user.role != "admin":
        q = q.filter(Farm.owner_id == user.id)
    elif owner_id:
        q = q.filter(Farm.owner_id == owner_id)
    total = q.count()
    items = q.order_by(Farm.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page[FarmOut](
        items=[_farm_out(f) for f in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.post("", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(body: FarmCreate, user: CurrentUser, db: DbSession) -> FarmOut:
    if user.role not in ("farmer", "admin"):
        raise forbidden("Only farmers can create farms", "farmers_only")
    farm = Farm(
        owner_id=user.id,
        name=body.name.strip(),
        region=body.region.strip(),
        district=body.district.strip(),
        area_hectares=body.area_hectares,
        notes=body.notes,
        boundary=body.boundary,
        center_lat=body.center_lat,
        center_lng=body.center_lng,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return _farm_out(farm)


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: str, user: CurrentUser, db: DbSession) -> FarmOut:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise not_found("Farm not found")
    if not _can_access(user, farm):
        raise forbidden("Not your farm", "forbidden")
    return _farm_out(farm)


@router.patch("/{farm_id}", response_model=FarmOut)
def update_farm(farm_id: str, body: FarmUpdate, user: CurrentUser, db: DbSession) -> FarmOut:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise not_found("Farm not found")
    if not _can_access(user, farm):
        raise forbidden("Not your farm", "forbidden")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(farm, field, value)
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return _farm_out(farm)


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(farm_id: str, user: CurrentUser, db: DbSession) -> None:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise not_found("Farm not found")
    if not _can_access(user, farm):
        raise forbidden("Not your farm", "forbidden")
    db.delete(farm)
    db.commit()
