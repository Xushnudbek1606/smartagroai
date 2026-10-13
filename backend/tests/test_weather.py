from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers


def test_weather_not_configured_returns_503(client, farmer):
    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/weather/current?location=Toshkent", headers=h)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "weather_not_configured"
    resp = client.get("/api/v1/weather/forecast?location=Toshkent", headers=h)
    assert resp.status_code == 503


def test_weather_requires_auth(client):
    assert client.get("/api/v1/weather/current?location=Toshkent").status_code == 401


def test_regions_listed(client, farmer):
    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/weather/regions", headers=h)
    assert resp.status_code == 200
    regions = resp.json()
    assert any(r["region"] == "Toshkent shahri" for r in regions)
    assert all(r["districts"] for r in regions)


def test_weather_current_with_mock_provider(client, farmer, monkeypatch):
    from app.integrations import weather as wmod

    class FakeService:
        def current(self, db, location):
            now = datetime.now(timezone.utc).isoformat()
            return {
                "location": location,
                "provider": "openweathermap",
                "temperature": 31.5,
                "feels_like": 33.0,
                "humidity": 40,
                "wind_speed": 3.2,
                "description": "clear sky",
                "icon": "01d",
                "cloudiness": 5,
                "precipitation_probability": None,
                "sun_rise": "",
                "sun_set": "",
                "fetched_at": now,
                "expires_at": now,
            }

        def forecast(self, db, location):
            now = datetime.now(timezone.utc).isoformat()
            return {
                "location": location,
                "provider": "openweathermap",
                "days": [
                    {
                        "date": "2026-10-10",
                        "temp_min": 18.0,
                        "temp_max": 33.0,
                        "description": "light rain",
                        "icon": "10d",
                        "precipitation_probability": 70,
                        "humidity": 65,
                        "wind_speed": 4.1,
                    }
                ],
                "advisories": ["Ya'g'in ehtimoli yuqori: sug'ish va kimyoviy ishlarni rejalashtirmang."],
                "fetched_at": now,
                "expires_at": now,
            }

    import app.api.v1.weather as weather_router

    monkeypatch.setattr(weather_router, "weather_service", FakeService())
    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/weather/current?location=Samarqand", headers=h)
    assert resp.status_code == 200
    assert resp.json()["temperature"] == 31.5
    resp = client.get("/api/v1/weather/forecast?location=Samarqand", headers=h)
    assert resp.status_code == 200
    assert resp.json()["days"][0]["precipitation_probability"] == 70
    assert resp.json()["advisories"]


def test_weather_provider_error_propagates(client, farmer, monkeypatch):
    from app.integrations.weather import WeatherServiceError
    from app.integrations import weather as wmod

    class ErrService:
        def current(self, db, location):
            raise WeatherServiceError("weather_location_not_found", "Hudud topilmadi", 404)

    import app.api.v1.weather as weather_router

    monkeypatch.setattr(weather_router, "weather_service", ErrService())
    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/weather/current?location=Nowhere", headers=h)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "weather_location_not_found"


def test_advisory_builder():
    from app.integrations.weather import build_advisories

    adv = build_advisories(
        {"temperature": 39, "humidity": 90, "wind_speed": 12},
        [{"precipitation_probability": 80}],
    )
    assert len(adv) >= 3
    calm = build_advisories({"temperature": 24, "humidity": 50, "wind_speed": 2}, [])
    assert calm  # always at least one advisory
