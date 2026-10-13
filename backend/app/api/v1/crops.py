from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import bad_request, forbidden, not_found
from app.models import Crop, Farm, User
from app.schemas import CropCreate, CropOut, CropUpdate, Page

router = APIRouter(prefix="/crops", tags=["crops"])


def _farm_owns(user: User, farm: Farm) -> bool:
    return user.role == "admin" or farm.owner_id == user.id


def _crop_out(crop: Crop) -> CropOut:
    out = CropOut.model_validate(crop)
    out.farm_name = crop.farm.name if crop.farm else None
    return out


@router.get("", response_model=Page[CropOut])
def list_crops(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    farm_id: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
) -> Page[CropOut]:
    q = db.query(Crop).join(Farm, Crop.farm_id == Farm.id)
    if user.role != "admin":
        q = q.filter(Farm.owner_id == user.id)
    if farm_id:
        q = q.filter(Crop.farm_id == farm_id)
    if status_:
        q = q.filter(Crop.status == status_)
    if search:
        q = q.filter(Crop.name.ilike(f"%{search.strip()}%"))
    total = q.count()
    items = q.order_by(Crop.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page[CropOut](
        items=[_crop_out(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.post("", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def create_crop(body: CropCreate, user: CurrentUser, db: DbSession) -> CropOut:
    farm = db.get(Farm, body.farm_id)
    if farm is None:
        raise not_found("Farm not found")
    if not _farm_owns(user, farm):
        raise forbidden("Not your farm", "forbidden")
    crop = Crop(
        farm_id=farm.id,
        name=body.name.strip(),
        variety=body.variety,
        planting_date=body.planting_date,
        area_hectares=body.area_hectares,
        status=body.status,
        notes=body.notes,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return _crop_out(crop)


@router.get("/{crop_id}", response_model=CropOut)
def get_crop(crop_id: str, user: CurrentUser, db: DbSession) -> CropOut:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise not_found("Crop not found")
    if not _farm_owns(user, crop.farm):
        raise forbidden("Not your crop", "forbidden")
    return _crop_out(crop)


@router.patch("/{crop_id}", response_model=CropOut)
def update_crop(crop_id: str, body: CropUpdate, user: CurrentUser, db: DbSession) -> CropOut:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise not_found("Crop not found")
    if not _farm_owns(user, crop.farm):
        raise forbidden("Not your crop", "forbidden")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(crop, field, value)
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return _crop_out(crop)


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop(crop_id: str, user: CurrentUser, db: DbSession) -> None:
    crop = db.get(Crop, crop_id)
    if crop is None:
        raise not_found("Crop not found")
    if not _farm_owns(user, crop.farm):
        raise forbidden("Not your crop", "forbidden")
    db.delete(crop)
    db.commit()
