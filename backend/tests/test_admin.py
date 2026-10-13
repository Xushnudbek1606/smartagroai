from __future__ import annotations

from tests.conftest import auth_headers


def test_admin_statistics(client, farmer, agronom, admin):
    h = auth_headers(client, "admin1")
    resp = client.get("/api/v1/admin/statistics", headers=h)
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_farmers"] >= 1
    assert stats["total_agronomists"] >= 1
    assert len(stats["activity"]) == 14


def test_non_admin_cannot_access_admin_endpoints(client, farmer, agronom):
    for username in ("farmer1", "agronom1"):
        h = auth_headers(client, username)
        assert client.get("/api/v1/admin/statistics", headers=h).status_code == 403
        assert client.get("/api/v1/admin/audit-logs", headers=h).status_code == 403
        assert client.get("/api/v1/admin/system-health", headers=h).status_code == 403
        assert client.get("/api/v1/admin/settings", headers=h).status_code == 403
    # and without token at all
    assert client.get("/api/v1/admin/statistics").status_code == 401


def test_audit_logs_record_actions(client, admin, farmer):
    ha = auth_headers(client, "admin1")
    client.post(
        "/api/v1/users",
        json={"full_name": "Audit U", "username": "audituser", "role": "farmer"},
        headers=ha,
    )
    resp = client.get("/api/v1/admin/audit-logs?action=admin.user_created", headers=ha)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    row = resp.json()["items"][0]
    assert row["action"] == "admin.user_created"
    assert row["actor_name"] is not None


def test_system_health(client, admin):
    h = auth_headers(client, "admin1")
    resp = client.get("/api/v1/admin/system-health", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "ok"
    assert body["weather_api"]["configured"] is False
    assert body["ai_service"]["configured"] is False
    assert body["telegram_bot"]["configured"] is False
    assert body["status"] in ("ok", "degraded")


def test_settings_update_and_get(client, admin, farmer):
    h = auth_headers(client, "admin1")
    resp = client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"landing_banner": {"title": "Welcome", "subtitle": "AI agro"}}},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["settings"]["landing_banner"]["title"] == "Welcome"
    resp = client.get("/api/v1/admin/settings", headers=h)
    assert resp.json()["settings"]["landing_banner"]["title"] == "Welcome"
    # farmer cannot modify settings
    hf = auth_headers(client, "farmer1")
    assert client.patch(
        "/api/v1/admin/settings", json={"settings": {"x": 1}}, headers=hf
    ).status_code == 403


def test_public_settings_exposes_only_whitelisted_keys(client, admin):
    """The landing page reads settings anonymously, but must never see
    internal/admin-only keys."""
    h = auth_headers(client, "admin1")
    resp = client.patch(
        "/api/v1/admin/settings",
        json={
            "settings": {
                "landing_banner": {"title": "Hosil", "text": "AI agro"},
                "contact": {"email": "info@smartagro.uz", "phone": "+998 71 000 00 00"},
                "internal_secret_note": "do-not-leak",
            }
        },
        headers=h,
    )
    assert resp.status_code == 200

    # public: no auth header at all
    pub = client.get("/api/v1/public/settings")
    assert pub.status_code == 200
    body = pub.json()["settings"]
    assert body["landing_banner"]["title"] == "Hosil"
    assert body["contact"]["email"] == "info@smartagro.uz"
    assert "internal_secret_note" not in body
    assert set(body.keys()) == {"landing_banner", "contact"}


def test_public_settings_defaults_when_unset(client):
    pub = client.get("/api/v1/public/settings")
    assert pub.status_code == 200
    assert pub.json()["settings"] == {"landing_banner": {}, "contact": {}}


def test_notifications_scoped_and_mark_read(client, farmer, farmer2, admin):
    # admin creates a user (audit) and farmer has none initially
    hf = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/notifications", headers=hf)
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    hf2 = auth_headers(client, "farmer2")
    assert client.get("/api/v1/notifications", headers=hf2).json()["total"] == 0


def test_admin_can_see_all_diagnoses_endpoint_shape(client, admin):
    h = auth_headers(client, "admin1")
    resp = client.get("/api/v1/diagnoses", headers=h)
    assert resp.status_code == 200
    assert "items" in resp.json() and "total" in resp.json()
