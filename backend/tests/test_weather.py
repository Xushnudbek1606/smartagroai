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


def test_weather_geo_endpoints_with_mock_provider(client, farmer, monkeypatch):
    class FakeGeoService:
        def current_by_coords(self, db, lat, lon):
            now = datetime.now(timezone.utc).isoformat()
            return {
                "location": f"Tashkent, UZ",
                "provider": "openweathermap",
                "temperature": 21.0,
                "feels_like": 20.0,
                "humidity": 35,
                "wind_speed": 2.1,
                "description": "clear sky",
                "icon": "01d",
                "cloudiness": 0,
                "precipitation_probability": None,
                "sun_rise": "",
                "sun_set": "",
                "fetched_at": now,
                "expires_at": now,
            }

        def forecast_by_coords(self, db, lat, lon):
            now = datetime.now(timezone.utc).isoformat()
            return {
                "location": "Tashkent, UZ",
                "provider": "openweathermap",
                "days": [],
                "advisories": [],
                "fetched_at": now,
                "expires_at": now,
            }

    import app.api.v1.weather as weather_router

    monkeypatch.setattr(weather_router, "weather_service", FakeGeoService())
    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/weather/current?lat=41.31&lon=69.24", headers=h)
    assert resp.status_code == 200
    assert resp.json()["temperature"] == 21.0
    resp = client.get("/api/v1/weather/forecast?lat=41.31&lon=69.24", headers=h)
    assert resp.status_code == 200


def test_weather_requires_location_or_coords(client, farmer):
    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/weather/current", headers=h)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "weather_location_required"
    resp = client.get("/api/v1/weather/forecast?lat=41.31", headers=h)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "weather_location_required"


def test_weather_rejects_out_of_range_coords(client, farmer):
    h = auth_headers(client, "farmer1")
    assert client.get("/api/v1/weather/current?lat=100&lon=69", headers=h).status_code == 422
    assert client.get("/api/v1/weather/current?lat=41&lon=200", headers=h).status_code == 422


def test_weather_by_coords_service(db, monkeypatch):
    """Real WeatherService: coords go to the provider, name comes from its reverse geocode."""
    from types import SimpleNamespace

    from app.integrations import weather as wmod

    monkeypatch.setattr(
        wmod,
        "get_settings",
        lambda: SimpleNamespace(
            weather_configured=True,
            WEATHER_API_KEY="test-key",
            WEATHER_PROVIDER="openweathermap",
            WEATHER_CACHE_TTL_SECONDS=600,
            FORECAST_CACHE_TTL_SECONDS=3600,
        ),
    )
    assert wmod.geo_cache_key(41.311, 69.2401) == "geo:41.31,69.24"

    svc = wmod.WeatherService()
    calls = {"current": 0, "forecast": 0}

    def fake_fetch_current(location, coords=None):
        calls["current"] += 1
        assert coords == (41.31, 69.24)
        return {
            "name": "Tashkent",
            "sys": {"country": "UZ", "sunrise": 0, "sunset": 0},
            "main": {"temp": 21.0, "feels_like": 20.0, "humidity": 35},
            "wind": {"speed": 2.1},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "clouds": {"all": 0},
        }

    def fake_fetch_forecast(location, coords=None):
        calls["forecast"] += 1
        assert coords == (41.31, 69.24)
        return {"city": {"name": "Tashkent", "country": "UZ"}, "list": []}

    monkeypatch.setattr(svc, "_fetch_current", fake_fetch_current)
    monkeypatch.setattr(svc, "_fetch_forecast", fake_fetch_forecast)

    payload = svc.current_by_coords(db, 41.31, 69.24)
    assert payload["location"] == "Tashkent, UZ"
    assert payload["temperature"] == 21.0
    # second call within TTL is served from the DB cache
    svc.current_by_coords(db, 41.31, 69.24)
    assert calls["current"] == 1

    payload = svc.forecast_by_coords(db, 41.31, 69.24)
    assert payload["location"] == "Tashkent, UZ"
    assert calls["forecast"] == 1


def test_weather_by_coords_falls_back_to_coord_label(db, monkeypatch):
    from types import SimpleNamespace

    from app.integrations import weather as wmod

    monkeypatch.setattr(
        wmod,
        "get_settings",
        lambda: SimpleNamespace(
            weather_configured=True,
            WEATHER_API_KEY="test-key",
            WEATHER_PROVIDER="openweathermap",
            WEATHER_CACHE_TTL_SECONDS=600,
            FORECAST_CACHE_TTL_SECONDS=3600,
        ),
    )
    svc = wmod.WeatherService()
    monkeypatch.setattr(
        svc,
        "_fetch_current",
        lambda location, coords=None: {
            "name": "",
            "sys": {},
            "main": {"temp": 10.0},
            "wind": {},
            "weather": [],
            "clouds": {},
        },
    )
    payload = svc.current_by_coords(db, 40.5, 71.25)
    assert payload["location"] == "40.50°, 71.25°"


def test_rain_periods_merges_adjacent_slots():
    from app.integrations.weather import rain_periods

    assert rain_periods([]) == []
    assert rain_periods([12, 15]) == ["12:00–18:00"]
    assert rain_periods([12, 15, 21]) == ["12:00–18:00", "21:00–00:00"]
    assert rain_periods([3, 12]) == ["03:00–06:00", "12:00–15:00"]


def test_forecast_normalization_reports_rain_windows():
    from app.integrations.weather import weather_service

    raw = {
        "list": [
            {
                "dt_txt": "2026-10-14 09:00:00",
                "main": {"temp_min": 10.0, "temp_max": 15.0, "humidity": 60},
                "weather": [{"description": "clouds", "icon": "02d"}],
                "pop": 0.1,
                "wind": {"speed": 3.0},
            },
            {
                "dt_txt": "2026-10-14 12:00:00",
                "main": {"temp_min": 11.0, "temp_max": 16.0, "humidity": 70},
                "weather": [{"description": "rain", "icon": "10d"}],
                "pop": 0.8,
                "wind": {"speed": 4.0},
            },
            {
                "dt_txt": "2026-10-14 15:00:00",
                "main": {"temp_min": 12.0, "temp_max": 17.0, "humidity": 75},
                "weather": [{"description": "rain", "icon": "10d"}],
                "pop": 0.6,
                "wind": {"speed": 5.0},
            },
            {
                "dt_txt": "2026-10-15 06:00:00",
                "main": {"temp_min": 9.0, "temp_max": 14.0, "humidity": 50},
                "weather": [{"description": "clear", "icon": "01d"}],
                "pop": 0.0,
                "wind": {"speed": 2.0},
            },
        ]
    }
    payload = weather_service._normalize_forecast("Toshkent", raw)
    today, tomorrow = payload["days"]
    assert today["precipitation_probability"] == 80
    assert today["rain_periods"] == ["12:00–18:00"]
    assert tomorrow["precipitation_probability"] == 0
    assert tomorrow["rain_periods"] == []
    # no internal helper keys leak into the API payload
    assert all("_rainy_hours" not in d for d in payload["days"])


def test_location_candidates_prefer_district_then_region():
    from app.integrations.weather import WeatherService

    assert WeatherService._location_candidates("Surxondaryo, Termiz") == [
        "Surxondaryo, Termiz",
        "Termiz",
        "Surxondaryo",
    ]
    assert WeatherService._location_candidates("Xorazm, Qo'shko'pir") == [
        "Xorazm, Qo'shko'pir",
        "Qo'shko'pir",
        "Qoshkopir",
        "Xorazm, Qoshkopir",
        "Xorazm",
    ]
    assert WeatherService._location_candidates("Toshkent") == ["Toshkent"]


def test_name_lookup_falls_back_to_geocode(db, monkeypatch):
    """A name the city DB misses is geocoded and retried by coordinates."""
    import httpx
    from types import SimpleNamespace

    from app.integrations import weather as wmod

    monkeypatch.setattr(
        wmod,
        "get_settings",
        lambda: SimpleNamespace(
            weather_configured=True,
            WEATHER_API_KEY="test-key",
            WEATHER_PROVIDER="openweathermap",
            WEATHER_CACHE_TTL_SECONDS=600,
            FORECAST_CACHE_TTL_SECONDS=3600,
        ),
    )
    geo_queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/direct"):
            q = request.url.params["q"]
            geo_queries.append(q)
            if q == "Termiz":
                return httpx.Response(
                    200,
                    json=[{"name": "Termez", "country": "UZ", "lat": 37.244, "lon": 67.283}],
                )
            return httpx.Response(200, json=[])
        if path.endswith("/weather"):
            if request.url.params.get("q"):  # composed name unknown to the city DB
                return httpx.Response(404, json={"cod": "404"})
            assert request.url.params.get("lat") == "37.244", "fallback must query by coordinates"
            return httpx.Response(
                200,
                json={
                    "name": "Termez",
                    "sys": {"country": "UZ"},
                    "main": {"temp": 25.0, "feels_like": 24.0, "humidity": 30},
                    "wind": {"speed": 3.0},
                    "weather": [{"description": "clear", "icon": "01d"}],
                    "clouds": {"all": 0},
                },
            )
        raise AssertionError(f"unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(wmod.httpx, "Client", lambda **kw: real_client(transport=transport))

    svc = wmod.WeatherService()
    payload = svc.current(db, "Surxondaryo, Termiz")
    assert payload["location"] == "Surxondaryo, Termiz"  # the name the user picked
    assert payload["temperature"] == 25.0
    assert geo_queries == ["Surxondaryo, Termiz", "Termiz"]


def test_advisory_builder():
    from app.integrations.weather import build_advisories

    adv = build_advisories(
        {"temperature": 39, "humidity": 90, "wind_speed": 12},
        [{"precipitation_probability": 80}],
    )
    assert len(adv) >= 3
    calm = build_advisories({"temperature": 24, "humidity": 50, "wind_speed": 2}, [])
    assert calm  # always at least one advisory
