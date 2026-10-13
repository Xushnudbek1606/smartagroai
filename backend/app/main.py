from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.api.v1.ws import router as ws_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("SmartAgroAI API starting (env=%s)", settings.ENVIRONMENT)
    # Seed the initial admin account (SEED_ADMIN_USERNAME / SEED_ADMIN_PASSWORD)
    # on startup — no-op if it already exists or the password is not set.
    try:
        from app.db.init_db import ensure_admin
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            ensure_admin(db)
    except Exception:  # seeding must never block startup (e.g. DB not migrated yet)
        logger.exception("Admin seed step failed")
    yield


app = FastAPI(
    title="SmartAgroAI API",
    description="AI-powered agriculture platform API — farmers, agronomists, diagnoses, weather and chat.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

register_exception_handlers(app)

# static uploads (plant images, avatars)
uploads_dir = settings.upload_dir
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(ws_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "ai_configured": settings.ai_configured,
        "weather_configured": settings.weather_configured,
        "telegram_configured": settings.telegram_configured,
    }
