from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1


class MessageOut(BaseModel):
    detail: str


# ---------------- subscription ----------------

class SubscriptionOut(BaseModel):
    plan: str
    role: str = "farmer"
    diagnoses_used: int
    diagnoses_limit: int  # -1 = unlimited
    advice_used: int
    advice_limit: int  # -1 = unlimited
    diagnoses_remaining: int | None = None
    advice_remaining: int | None = None
    unlimited: bool = False
    paid_until: str | None = None
    features: list[str] = ["diagnoses", "advice"]


class SubscriptionAdminOut(SubscriptionOut):
    user_id: str
    username: str | None = None


class SubscriptionAdminUpdate(BaseModel):
    plan: str | None = Field(default=None, pattern=r"^(free|pro)$")
    diagnoses_limit: int | None = Field(default=None, ge=-1)
    advice_limit: int | None = Field(default=None, ge=-1)
    paid_until: datetime | None = None
    reset_usage: bool = False


# ---------------- auth ----------------

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# ---------------- users ----------------

class UserOut(ORMModel):
    id: str
    full_name: str
    username: str
    role: str
    telegram_id: str | None = None
    telegram_username: str | None = None
    phone: str | None = None
    region: str | None = None
    district: str | None = None
    preferred_language: str
    avatar_url: str | None = None
    is_active: bool
    must_change_password: bool
    telegram_notifications_enabled: bool
    created_at: datetime


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9_.-]+$")
    role: str = Field(pattern=r"^(admin|farmer|agronom)$")
    phone: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    preferred_language: str = Field(default="uz-Latn", pattern=r"^(uz-Latn|uz-Cyrl|en|ru)$")
    # Telegram @username (without @) — hint so /account CODE only completes
    # from the matching Telegram account. Must be set BEFORE linking.
    telegram_username: str | None = Field(default=None, min_length=4, max_length=64)


class UserCreateOut(BaseModel):
    user: UserOut
    invitation_code: str | None = None
    invitation_expires_at: datetime | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, pattern=r"^(uz-Latn|uz-Cyrl|en|ru)$")
    avatar_url: str | None = Field(default=None, max_length=512)
    telegram_notifications_enabled: bool | None = None


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, pattern=r"^(admin|farmer|agronom)$")
    is_active: bool | None = None
    phone: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, pattern=r"^(uz-Latn|uz-Cyrl|en|ru)$")
    # Only changeable while the account is NOT yet linked to Telegram —
    # after linking the real @username comes from Telegram itself.
    telegram_username: str | None = Field(default=None, min_length=4, max_length=64)


class PasswordResetOut(BaseModel):
    username: str
    temporary_password: str
    must_change_password: bool = True


# ---------------- invitations ----------------

class InvitationCreate(BaseModel):
    user_id: str
    purpose: str = Field(default="telegram_link", pattern=r"^(telegram_link|password_reset)$")


class InvitationOut(ORMModel):
    id: str
    user_id: str
    purpose: str
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime


class InvitationCreateOut(BaseModel):
    invitation: InvitationOut
    code: str  # shown once to the admin; only its hash is stored


class InvitationClaimRequest(BaseModel):
    code: str = Field(min_length=4, max_length=64)
    telegram_id: str = Field(min_length=5, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)


class InvitationClaimOut(BaseModel):
    username: str
    temporary_password: str
    language: str
    full_name: str


class InvitationStatusOut(BaseModel):
    linked: bool
    username: str | None = None
    language: str | None = None


# ---------------- farms / crops ----------------

class FarmCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    area_hectares: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    # GeoJSON geometry drawn on the map: {"type":"Polygon","coordinates":[...]}
    # or {"type":"Point","coordinates":[lng,lat]}
    boundary: dict[str, Any] | None = Field(default=None)
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lng: float | None = Field(default=None, ge=-180, le=180)


class FarmUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    region: str | None = Field(default=None, min_length=2, max_length=80)
    district: str | None = Field(default=None, min_length=1, max_length=80)
    area_hectares: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    boundary: dict[str, Any] | None = None
    center_lat: float | None = Field(default=None, ge=-90, le=90)
    center_lng: float | None = Field(default=None, ge=-180, le=180)


class FarmOut(ORMModel):
    id: str
    owner_id: str
    name: str
    region: str
    district: str
    area_hectares: float | None = None
    notes: str | None = None
    boundary: dict[str, Any] | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    created_at: datetime
    updated_at: datetime
    crops_count: int = 0


class CropCreate(BaseModel):
    farm_id: str
    name: str = Field(min_length=1, max_length=120)
    variety: str | None = Field(default=None, max_length=120)
    planting_date: datetime | None = None
    area_hectares: float | None = Field(default=None, ge=0)
    status: str = Field(default="growing", pattern=r"^(planned|growing|harvested|failed)$")
    notes: str | None = Field(default=None, max_length=2000)


class CropUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    variety: str | None = Field(default=None, max_length=120)
    planting_date: datetime | None = None
    area_hectares: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern=r"^(planned|growing|harvested|failed)$")
    notes: str | None = Field(default=None, max_length=2000)


class CropOut(ORMModel):
    id: str
    farm_id: str
    name: str
    variety: str | None = None
    planting_date: datetime | None = None
    area_hectares: float | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    farm_name: str | None = None


# ---------------- diagnoses ----------------

class DiagnosisOut(ORMModel):
    id: str
    farmer_id: str
    crop_id: str | None = None
    image_url: str
    predicted_crop: str | None = None
    disease_name: str | None = None
    confidence: float | None = None
    severity: str | None = None
    symptoms: list[Any] | None = None
    recommendations: list[Any] | None = None
    next_steps: str | None = None
    region: str | None = None
    user_notes: str | None = None
    model_version: str | None = None
    status: str
    language: str
    created_at: datetime


class IntegrationStatusOut(BaseModel):
    configured: bool
    provider: str | None = None
    model: str | None = None


# ---------------- weather ----------------

class WeatherCurrentOut(BaseModel):
    location: str
    provider: str
    fetched_at: datetime
    expires_at: datetime
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    description: str
    icon: str | None = None
    precipitation_probability: int | None = None
    cloudiness: int | None = None
    sun_rise: str | None = None
    sun_set: str | None = None


class WeatherDayOut(BaseModel):
    date: str
    temp_min: float
    temp_max: float
    description: str
    icon: str | None = None
    precipitation_probability: int | None = None
    humidity: int | None = None
    wind_speed: float | None = None


class WeatherForecastOut(BaseModel):
    location: str
    provider: str
    fetched_at: datetime
    expires_at: datetime
    days: list[WeatherDayOut]
    advisories: list[str] = []


class WeatherLocationOut(BaseModel):
    region: str
    districts: list[str]


# ---------------- chat ----------------

class ConversationOut(BaseModel):
    id: str
    farmer_id: str
    agronomist_id: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None
    unread_count: int = 0
    partner: UserOut | None = None
    last_message_preview: str | None = None


class ConversationCreate(BaseModel):
    agronomist_id: str


class ChatMessageOut(ORMModel):
    id: str
    conversation_id: str
    sender_id: str
    message_text: str | None = None
    attachment_url: str | None = None
    attachment_name: str | None = None
    read_at: datetime | None = None
    created_at: datetime


class WSChatEvent(BaseModel):
    event: str
    conversation_id: str | None = None
    message: ChatMessageOut | None = None
    data: dict[str, Any] | None = None


# ---------------- notifications ----------------

class NotificationOut(ORMModel):
    id: str
    title: str
    body: str | None = None
    type: str
    link: str | None = None
    is_read: bool
    created_at: datetime


# ---------------- admin ----------------

class AdminStatisticsOut(BaseModel):
    total_users: int
    total_farmers: int
    total_agronomists: int
    total_admins: int
    active_users: int
    total_farms: int
    total_crops: int
    total_diagnoses: int
    diagnoses_today: int
    diagnoses_week: int
    total_conversations: int
    messages_total: int
    users_registered_today: int
    activity: list[dict[str, Any]] = []


class AuditLogOut(ORMModel):
    id: str
    actor_id: str | None = None
    actor_name: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    detail: dict[str, Any] | None = None
    created_at: datetime


class SystemHealthOut(BaseModel):
    status: str
    database: str
    weather_api: IntegrationStatusOut
    ai_service: IntegrationStatusOut
    telegram_bot: dict[str, Any]
    redis: str
    version: str = "1.0.0"
    environment: str = "development"
    checked_at: datetime


class SettingsOut(BaseModel):
    settings: dict[str, Any]


class SettingsUpdate(BaseModel):
    settings: dict[str, Any]


class TelegramHeartbeat(BaseModel):
    bot_started_at: datetime | None = None
    version: str | None = None


class TelegramPreferencesRequest(BaseModel):
    telegram_id: str = Field(min_length=5, max_length=32)
    enabled: bool


class TelegramLanguageRequest(BaseModel):
    telegram_id: str = Field(min_length=5, max_length=32)
    language: str = Field(min_length=2, max_length=10)
