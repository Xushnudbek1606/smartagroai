from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile, status

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, rate_limiter
from app.core.errors import bad_request, forbidden, not_found
from app.integrations.ai import AIIntegrationError, plant_ai_service
from app.models import Crop, Diagnosis, User
from app.schemas import DiagnosisOut, IntegrationStatusOut, Page
from app.services import files, subscription_service
from app.services.notifications import notify_diagnosis_done

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


def _diag_out(d: Diagnosis) -> DiagnosisOut:
    return DiagnosisOut.model_validate(d)


@router.get("/integration-status", response_model=IntegrationStatusOut)
def integration_status(user: CurrentUser) -> IntegrationStatusOut:
    s = get_settings()
    return IntegrationStatusOut(
        configured=s.ai_configured,
        provider=s.AI_PROVIDER if s.ai_configured else None,
        model=s.AI_MODEL_NAME if s.ai_configured else None,
    )


@router.post("", response_model=DiagnosisOut, status_code=status.HTTP_201_CREATED)
async def create_diagnosis(
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    crop_type: Annotated[str | None, Form()] = None,
    region: Annotated[str | None, Form()] = None,
    crop_id: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form(max_length=2000)] = None,
) -> DiagnosisOut:
    if user.role not in ("farmer", "agronom", "admin"):
        raise forbidden("Only farmers and agronomists can run diagnoses", "farmers_only")
    rate_limiter.check(f"diagnose:{user.id}", 20, 300)
    sub = None if subscription_service.has_unlimited_usage(user) else (
        subscription_service.check_diagnosis_quota(db, user)
    )

    data = await file.read()
    try:
        image_url, _name = files.save_image_file(data, file.filename or "photo")
    except files.FileValidationError as exc:
        raise bad_request(exc.message, exc.code)

    if crop_id:
        crop = db.get(Crop, crop_id)
        if crop is None or (user.role != "admin" and crop.farm.owner_id != user.id):
            raise bad_request("Crop not found among your crops", "crop_not_found")

    # Resolve stored path for the AI provider
    from pathlib import Path

    settings = get_settings()
    stored_path = settings.upload_dir / image_url.removeprefix("/static/")

    try:
        result = plant_ai_service.analyze(
            stored_path,
            crop_hint=crop_type,
            region=region or user.region,
            language=user.preferred_language,
        )
    except AIIntegrationError as exc:
        from app.core.errors import service_unavailable

        logger.info("AI analysis failed: %s", exc.code)
        raise service_unavailable(exc.message, exc.code)

    diagnosis = Diagnosis(
        farmer_id=user.id,
        crop_id=crop_id,
        image_url=image_url,
        predicted_crop=result.predicted_crop or crop_type,
        disease_name=result.disease_name,
        confidence=result.confidence,
        severity=result.severity,
        symptoms=result.symptoms,
        recommendations=result.recommendations,
        next_steps=result.next_steps,
        region=region or user.region,
        user_notes=notes,
        model_version=result.model_version,
        # No clear disease/plant in the photo → keep the record but flag it so
        # the UI can warn "retake the photo" instead of showing an "Unknown"
        # diagnosis.
        status="no_finding" if result.disease_name is None else "completed",
        language=user.preferred_language,
    )
    db.add(diagnosis)
    if sub is not None:
        subscription_service.record_diagnosis_use(db, sub)
    db.commit()
    db.refresh(diagnosis)

    background.add_task(
        notify_diagnosis_done, user, diagnosis.disease_name, diagnosis.confidence
    )
    return _diag_out(diagnosis)


@router.get("", response_model=Page[DiagnosisOut])
def list_diagnoses(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    farmer_id: str | None = Query(default=None),
    crop_id: str | None = Query(default=None),
) -> Page[DiagnosisOut]:
    q = db.query(Diagnosis)
    if user.role == "admin":
        if farmer_id:
            q = q.filter(Diagnosis.farmer_id == farmer_id)
    else:
        q = q.filter(Diagnosis.farmer_id == user.id)
    if crop_id:
        q = q.filter(Diagnosis.crop_id == crop_id)
    total = q.count()
    items = q.order_by(Diagnosis.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page[DiagnosisOut](
        items=[_diag_out(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/{diagnosis_id}", response_model=DiagnosisOut)
def get_diagnosis(diagnosis_id: str, user: CurrentUser, db: DbSession) -> DiagnosisOut:
    d = db.get(Diagnosis, diagnosis_id)
    if d is None:
        raise not_found("Diagnosis not found")
    if user.role != "admin" and d.farmer_id != user.id:
        raise forbidden("Not your diagnosis", "forbidden")
    return _diag_out(d)


@router.delete("/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diagnosis(diagnosis_id: str, user: CurrentUser, db: DbSession) -> None:
    d = db.get(Diagnosis, diagnosis_id)
    if d is None:
        raise not_found("Diagnosis not found")
    if user.role != "admin" and d.farmer_id != user.id:
        raise forbidden("Not your diagnosis", "forbidden")
    db.delete(d)
    db.commit()
