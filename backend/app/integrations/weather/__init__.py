from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import WeatherCache

logger = logging.getLogger(__name__)

WEATHER_API_UNAVAILABLE = "weather_api_unavailable"
WEATHER_NOT_CONFIGURED = "weather_not_configured"

# Uzbekistan locations served by the weather module
UZBEKISTAN_LOCATIONS: list[dict[str, Any]] = [
    {"region": "Toshkent shahri", "districts": ["Yunusobod", "Chilonzor", "Mirzo Ulug'bek", "Shayxontohur", "Yakkasaroy"]},
    {"region": "Toshkent viloyati", "districts": ["Olmaliq", "Chirchiq", "Bekabad", "Yangiyol", "Qibray"]},
    {"region": "Andijon", "districts": ["Andijon", "Xo'jaobod", "Bo'ston", "Jalaquduq", "Paxtazor"]},
    {"region": "Farg'ona", "districts": ["Farg'ona", "Qo'qon", "Marg'ilon", "Beshariq", "Quva"]},
    {"region": "Namangan", "districts": ["Namangan", "Chortoq", "Uchqo'rg'on", "Kosonsoy", "Mingbuloq"]},
    {"region": "Samarqand", "districts": ["Samarqand", "Urgut", "Kattaqo'rg'on", "Jomboy", "Ishtixon"]},
    {"region": "Buxoro", "districts": ["Buxoro", "Kogon", "G'ijduvon", "Vobkent", "Jondor"]},
    {"region": "Navoiy", "districts": ["Navoiy", "Karmana", "Uchqudur", "Qiziltepa", "Zarafshon"]},
    {"region": "Qashqadaryo", "districts": ["Qarshi", "Shahrisabz", "Kitob", "Qamashi", "G'uzor"]},
    {"region": "Surxondaryo", "districts": ["Termiz", "Denov", "Sherobod", "Boysun", "Qumqo'rg'on"]},
    {"region": "Jizzax", "districts": ["Jizzax", "G'azallon", "Forish", "Zomin", "Baxmal"]},
    {"region": "Sirdaryo", "districts": ["Sirdaryo", "Guliston", "Yangiyer", "Sardoba", "Oqoltin"]},
    {"region": "Xorazm", "districts": ["Urganch", "Xiva", "Beshqo'rg'on", "Gurlan", "Qo'shko'pir"]},
    {"region": "Qoraqalpog'iston", "districts": ["Nukus", "Xo'jayli", "Qo'ng'irot", "Amudaryo", "Beyneu"]},
]


GEO_BASE_URL = "https://api.openweathermap.org/geo/1.0/direct"


class WeatherServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def geo_cache_key(lat: float, lon: float) -> str:
    """Cache key for coordinate lookups (~1.1 km grid at 2 decimals)."""
    return f"geo:{lat:.2f},{lon:.2f}"


def coords_label(lat: float, lon: float) -> str:
    return f"{lat:.2f}°, {lon:.2f}°"


# 3-hour slots at/above this chance count as "rain expected" for the day
RAIN_POP_THRESHOLD = 0.4


def rain_periods(slots: list[int]) -> list[str]:
    """Merge rainy 3-hour slots (provider local hours) into time windows.

    e.g. [12, 15, 21] -> ["12:00–18:00", "21:00–00:00"]
    """
    if not slots:
        return []
    hours = sorted(set(slots))
    periods: list[str] = []
    start = prev = hours[0]
    for hour in hours[1:]:
        if hour - prev <= 3:  # adjacent 3-hour slot — same rain window
            prev = hour
            continue
        periods.append(f"{start:02d}:00–{(prev + 3) % 24:02d}:00")
        start = prev = hour
    periods.append(f"{start:02d}:00–{(prev + 3) % 24:02d}:00")
    return periods


def _valid(cache: WeatherCache | None) -> bool:
    if cache is None:
        return False
    exp = cache.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > _utcnow()


def build_advisories(current: dict[str, Any], days: list[dict[str, Any]]) -> list[str]:
    """Weather-driven agronomy cautions. General and deliberately imprecise."""
    adv: list[str] = []
    temp = current.get("temperature")
    humidity = current.get("humidity")
    wind = current.get("wind_speed")
    if temp is not None and temp >= 36:
        adv.append("Issiqlik baland: sug'ishni erta tong yoki kechqurun bajaring.")
    if temp is not None and temp <= 2:
        adv.append("Tuzatish harorati past: sezqich ekinlarni himoya qiling.")
    if wind is not None and wind >= 10:
        adv.append("Kuchli shamol: purkovchi ishlarni bugun kechiktiring.")
    if humidity is not None and humidity >= 85:
        adv.append("Yuqori namlik: barg kasalliklari xavfi oshadi, dalani kuzating.")
    rain_next = any((d.get("precipitation_probability") or 0) >= 60 for d in days[:2])
    if rain_next:
        adv.append("Ya'g'in ehtimoli yuqori: sug'ish va kimyoviy ishlarni rejalashtirmang.")
    if not adv:
        adv.append("Ob-havo sharoiti qulay: odatiy parvarish ishlarni davom ettiring.")
    return adv


class WeatherService:
    """OpenWeatherMap-backed service with DB caching.

    Never returns fabricated data: if the provider or API key is missing,
    raises WeatherServiceError(503) so the UI can show the true status.
    """

    def current(self, db: Session, location: str) -> dict[str, Any]:
        return self._get(db, location, kind="current")

    def forecast(self, db: Session, location: str) -> dict[str, Any]:
        return self._get(db, location, kind="forecast")

    def current_by_coords(self, db: Session, lat: float, lon: float) -> dict[str, Any]:
        """Weather for an exact GPS position (browser geolocation)."""
        return self._get(db, geo_cache_key(lat, lon), kind="current", coords=(lat, lon))

    def forecast_by_coords(self, db: Session, lat: float, lon: float) -> dict[str, Any]:
        return self._get(db, geo_cache_key(lat, lon), kind="forecast", coords=(lat, lon))

    # ----- internals -----

    def _get(self, db: Session, location: str, kind: str, coords: tuple[float, float] | None = None) -> dict[str, Any]:
        settings = get_settings()
        if not settings.weather_configured:
            raise WeatherServiceError(
                WEATHER_NOT_CONFIGURED,
                "Ob-havo API kaliti sozlanmagan (WEATHER_API_KEY). Administrator sozlamalarni tekshirsin.",
            )
        location = location.strip()
        cached = (
            db.query(WeatherCache)
            .filter(WeatherCache.location == location, WeatherCache.kind == kind)
            .first()
        )
        if _valid(cached):
            payload = dict(cached.weather_payload)
            payload["fetched_at"] = cached.fetched_at.isoformat()
            payload["expires_at"] = cached.expires_at.isoformat()
            return payload

        if kind == "current":
            raw = self._fetch_current(location, coords=coords)
            payload = self._normalize_current(
                self._display_location(raw, kind, coords, location), raw
            )
            ttl = settings.WEATHER_CACHE_TTL_SECONDS
        else:
            raw = self._fetch_forecast(location, coords=coords)
            payload = self._normalize_forecast(
                self._display_location(raw, kind, coords, location), raw
            )
            ttl = settings.FORECAST_CACHE_TTL_SECONDS

        now = _utcnow()
        if cached:
            cached.weather_payload = payload
            cached.fetched_at = now
            cached.expires_at = now + timedelta(seconds=ttl)
        else:
            db.add(
                WeatherCache(
                    location=location,
                    kind=kind,
                    provider=settings.WEATHER_PROVIDER,
                    weather_payload=payload,
                    fetched_at=now,
                    expires_at=now + timedelta(seconds=ttl),
                )
            )
        db.commit()
        payload = dict(payload)
        payload["fetched_at"] = now.isoformat()
        payload["expires_at"] = (now + timedelta(seconds=ttl)).isoformat()
        return payload

    @staticmethod
    def _display_location(
        raw: dict[str, Any],
        kind: str,
        coords: tuple[float, float] | None,
        fallback: str,
    ) -> str:
        """Human-readable place name for coordinate lookups (provider reverse name)."""
        if coords is None:
            return fallback
        if kind == "current":
            name = raw.get("name") or ""
            country = (raw.get("sys") or {}).get("country") or ""
        else:
            city = raw.get("city") or {}
            name = city.get("name") or ""
            country = city.get("country") or ""
        label = ", ".join(part for part in (name, country) if part)
        return label or coords_label(*coords)

    @staticmethod
    def _query_params(
        location: str, coords: tuple[float, float] | None
    ) -> dict[str, Any]:
        if coords is not None:
            return {"lat": coords[0], "lon": coords[1]}
        return {"q": f"{location},UZ"}

    @staticmethod
    def _location_candidates(location: str) -> list[str]:
        """Progressively looser geocoding queries for a "Region, District" name.

        OpenWeatherMap's city DB cannot resolve every composed name
        (e.g. "Surxondaryo, Termiz"), so we retry with the bare district,
        an apostrophe-normalized variant and finally the bare region.
        """
        parts = [p.strip() for p in location.split(",") if p.strip()]
        candidates = [location]
        if len(parts) > 1:
            candidates.append(parts[-1])
            stripped = parts[-1].replace("'", "")
            if stripped != parts[-1]:
                candidates.append(stripped)
        stripped_full = location.replace("'", "")
        if stripped_full != location:
            candidates.append(stripped_full)
        if len(parts) > 1:
            candidates.append(parts[0])
        seen: set[str] = set()
        return [c for c in candidates if not (c in seen or seen.add(c))]

    def _geocode(self, client: httpx.Client, location: str) -> tuple[float, float] | None:
        """Resolve a place name to coordinates via the OWM Geo API, or None."""
        settings = get_settings()
        for query in self._location_candidates(location):
            try:
                resp = client.get(
                    GEO_BASE_URL,
                    params={"q": query, "limit": 1, "appid": settings.WEATHER_API_KEY},
                )
            except httpx.HTTPError:
                return None
            if resp.status_code != 200:
                continue
            hits = resp.json() or []
            if hits:
                return float(hits[0]["lat"]), float(hits[0]["lon"])
        return None

    def _weather_params(
        self, location: str, coords: tuple[float, float] | None
    ) -> dict[str, Any]:
        settings = get_settings()
        return {
            **self._query_params(location, coords),
            "appid": settings.WEATHER_API_KEY,
            "units": "metric",
            "lang": "uz",
        }

    def _fetch_current(
        self, location: str, coords: tuple[float, float] | None = None
    ) -> dict[str, Any]:
        params = self._weather_params(location, coords)
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(weather_url, params=params)
                if resp.status_code == 404 and coords is None:
                    # The composed name is unknown to the city DB: geocode it
                    # and retry by coordinates (display name stays requested).
                    resolved = self._geocode(client, location)
                    if resolved:
                        resp = client.get(
                            weather_url,
                            params=self._weather_params(location, resolved),
                        )
        except httpx.HTTPError as exc:
            raise WeatherServiceError(WEATHER_API_UNAVAILABLE, "Ob-havo xizmatiga ulanib bo'lmadi") from exc
        if resp.status_code == 401:
            raise WeatherServiceError("weather_auth_failed", "Ob-havo API kaliti noto'g'ri", 502)
        if resp.status_code == 404:
            raise WeatherServiceError("weather_location_not_found", "Hudud topilmadi", 404)
        if resp.status_code != 200:
            logger.warning("Weather current returned %s", resp.status_code)
            raise WeatherServiceError(WEATHER_API_UNAVAILABLE, "Ob-havo xizmati vaqtincha ishlamayapti")
        return resp.json()

    def _fetch_forecast(
        self, location: str, coords: tuple[float, float] | None = None
    ) -> dict[str, Any]:
        params = self._weather_params(location, coords)
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(forecast_url, params=params)
                if resp.status_code == 404 and coords is None:
                    resolved = self._geocode(client, location)
                    if resolved:
                        resp = client.get(
                            forecast_url,
                            params=self._weather_params(location, resolved),
                        )
        except httpx.HTTPError as exc:
            raise WeatherServiceError(WEATHER_API_UNAVAILABLE, "Ob-havo xizmatiga ulanib bo'lmadi") from exc
        if resp.status_code == 404:
            raise WeatherServiceError("weather_location_not_found", "Hudud topilmadi", 404)
        if resp.status_code != 200:
            raise WeatherServiceError(WEATHER_API_UNAVAILABLE, "Ob-havo xizmati vaqtincha ishlamayapti")
        return resp.json()

    def _normalize_current(self, location: str, raw: dict[str, Any]) -> dict[str, Any]:
        main = raw.get("main", {})
        wind = raw.get("wind", {})
        weather0 = (raw.get("weather") or [{}])[0]
        clouds = raw.get("clouds", {})
        sys_ = raw.get("sys", {})
        return {
            "location": location,
            "provider": get_settings().WEATHER_PROVIDER,
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "wind_speed": wind.get("speed"),
            "description": weather0.get("description") or "",
            "icon": weather0.get("icon"),
            "cloudiness": clouds.get("all"),
            "precipitation_probability": None,
            "sun_rise": str(sys_.get("sunrise") or ""),
            "sun_set": str(sys_.get("sunset") or ""),
        }

    def _normalize_forecast(self, location: str, raw: dict[str, Any]) -> dict[str, Any]:
        by_day: dict[str, dict[str, Any]] = {}
        for item in raw.get("list", []):
            dt_txt: str = item.get("dt_txt", "")
            if not dt_txt:
                continue
            day = dt_txt[:10]
            main = item.get("main", {})
            weather0 = (item.get("weather") or [{}])[0]
            pop = item.get("pop")
            d = by_day.setdefault(
                day,
                {
                    "date": day,
                    "temp_min": main.get("temp_min"),
                    "temp_max": main.get("temp_max"),
                    "description": weather0.get("description") or "",
                    "icon": weather0.get("icon"),
                    "precipitation_probability": None,
                    "humidity": main.get("humidity"),
                    "wind_speed": item.get("wind", {}).get("speed"),
                    "_rainy_hours": [],
                },
            )
            if main.get("temp_min") is not None:
                d["temp_min"] = min(d["temp_min"] or main["temp_min"], main["temp_min"])
            if main.get("temp_max") is not None:
                d["temp_max"] = max(d["temp_max"] or main["temp_max"], main["temp_max"])
            if pop is not None:
                p = int(round(pop * 100))
                d["precipitation_probability"] = max(d["precipitation_probability"] or 0, p)
                if pop >= RAIN_POP_THRESHOLD:
                    try:
                        d["_rainy_hours"].append(int(dt_txt[11:13]))
                    except ValueError:
                        pass
        days = sorted(by_day.values(), key=lambda d: d["date"])[:7]
        for d in days:
            d["rain_periods"] = rain_periods(d.pop("_rainy_hours", []))
        advisories = build_advisories({}, days)
        return {
            "location": location,
            "provider": get_settings().WEATHER_PROVIDER,
            "days": days,
            "advisories": advisories,
        }


weather_service = WeatherService()
