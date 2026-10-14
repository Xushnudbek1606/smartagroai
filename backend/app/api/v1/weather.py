from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.integrations.weather import UZBEKISTAN_LOCATIONS, WeatherServiceError, weather_service
from app.schemas import WeatherCurrentOut, WeatherDayOut, WeatherForecastOut, WeatherLocationOut

router = APIRouter(prefix="/weather", tags=["weather"])


def _wrap(err: WeatherServiceError) -> AppError:
    return AppError(err.status_code, err.code, err.message)


def _utcnow() -> datetime:
    """Timezone-aware UTC now (datetime.utcnow() is deprecated/naive in 3.12+)."""
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@router.get("/regions", response_model=list[WeatherLocationOut])
def regions(user: CurrentUser) -> list[WeatherLocationOut]:
    return [WeatherLocationOut(**loc) for loc in UZBEKISTAN_LOCATIONS]


def _require_location(location: str | None, lat: float | None, lon: float | None) -> None:
    if location is None and (lat is None or lon is None):
        raise AppError(
            400,
            "weather_location_required",
            "location yoki lat va lon parameterlari kerak",
        )


@router.get("/current", response_model=WeatherCurrentOut)
def current(
    db: DbSession,
    user: CurrentUser,
    location: str | None = Query(default=None, min_length=2, max_length=120),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
) -> WeatherCurrentOut:
    _require_location(location, lat, lon)
    try:
        if lat is not None and lon is not None:
            data = weather_service.current_by_coords(db, lat, lon)
        else:
            data = weather_service.current(db, location)
    except WeatherServiceError as err:
        raise _wrap(err)
    return WeatherCurrentOut(
        location=data["location"],
        provider=data["provider"],
        fetched_at=_parse_dt(data.get("fetched_at")) or _utcnow(),
        expires_at=_parse_dt(data.get("expires_at")) or _utcnow(),
        temperature=data.get("temperature"),
        feels_like=data.get("feels_like"),
        humidity=data.get("humidity") or 0,
        wind_speed=data.get("wind_speed") or 0,
        description=data.get("description") or "",
        icon=data.get("icon"),
        precipitation_probability=data.get("precipitation_probability"),
        cloudiness=data.get("cloudiness"),
        sun_rise=data.get("sun_rise"),
        sun_set=data.get("sun_set"),
    )


@router.get("/forecast", response_model=WeatherForecastOut)
def forecast(
    db: DbSession,
    user: CurrentUser,
    location: str | None = Query(default=None, min_length=2, max_length=120),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
) -> WeatherForecastOut:
    _require_location(location, lat, lon)
    try:
        if lat is not None and lon is not None:
            data = weather_service.forecast_by_coords(db, lat, lon)
        else:
            data = weather_service.forecast(db, location)
    except WeatherServiceError as err:
        raise _wrap(err)
    days = [WeatherDayOut(**d) for d in data.get("days", [])]
    return WeatherForecastOut(
        location=data["location"],
        provider=data["provider"],
        fetched_at=_parse_dt(data.get("fetched_at")) or _utcnow(),
        expires_at=_parse_dt(data.get("expires_at")) or _utcnow(),
        days=days,
        advisories=data.get("advisories", []),
    )
