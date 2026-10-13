from __future__ import annotations

import os

# Configure a test environment BEFORE app modules are imported.
os.environ["DATABASE_URL"] = "sqlite:///./test_smartagro.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["UPLOAD_STORAGE_PATH"] = "./test_uploads"
os.environ["AI_PROVIDER"] = "none"
os.environ["WEATHER_API_KEY"] = ""
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-internal-secret"
os.environ["LOGIN_RATE_LIMIT_ATTEMPTS"] = "1000"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import User


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_smartagro.db")
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _clean_tables():
    """Wipe all data between tests (SQLite does not enforce FK cascades)."""
    from app.models import (
        AgronomAssignment,
        AgronomistProfile,
        AuditLog,
        Conversation,
        Crop,
        Diagnosis,
        Farm,
        Invitation,
        Message,
        Notification,
        RefreshToken,
        Setting,
        SystemEvent,
        WeatherCache,
    )

    yield
    db: Session = SessionLocal()
    try:
        for model in (
            Message,
            Conversation,
            Diagnosis,
            Crop,
            Farm,
            Invitation,
            RefreshToken,
            Notification,
            AgronomAssignment,
            AgronomistProfile,
            AuditLog,
            Setting,
            SystemEvent,
            WeatherCache,
            User,
        ):
            db.query(model).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def make_user(
    db: Session,
    username: str,
    role: str,
    password: str = "Password123!",
    **kwargs,
) -> User:
    user = User(
        full_name=kwargs.pop("full_name", username.title()),
        username=username,
        password_hash=hash_password(password),
        role=role,
        preferred_language=kwargs.pop("preferred_language", "uz-Latn"),
        is_active=kwargs.pop("is_active", True),
        must_change_password=kwargs.pop("must_change_password", False),
        **kwargs,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def farmer(db):
    return make_user(db, "farmer1", "farmer")


@pytest.fixture
def farmer2(db):
    return make_user(db, "farmer2", "farmer")


@pytest.fixture
def agronom(db):
    return make_user(db, "agronom1", "agronom")


@pytest.fixture
def admin(db):
    return make_user(db, "admin1", "admin")


def login(client: TestClient, username: str, password: str = "Password123!") -> dict:
    resp = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(client: TestClient, username: str, password: str = "Password123!") -> dict:
    tokens = login(client, username, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
