from __future__ import annotations

from tests.conftest import auth_headers, login


def test_admin_creates_user_and_gets_invitation_code(client, admin):
    headers = auth_headers(client, "admin1")
    resp = client.post(
        "/api/v1/users",
        json={
            "full_name": "Yangi Fermer",
            "username": "newfarmer",
            "role": "farmer",
            "region": "Buxoro",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["username"] == "newfarmer"
    assert body["invitation_code"]
    assert body["user"]["must_change_password"] is True


def test_farmer_cannot_create_user(client, farmer):
    headers = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/users",
        json={"full_name": "XX", "username": "hacker", "role": "admin"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_duplicate_username_rejected(client, admin, farmer):
    headers = auth_headers(client, "admin1")
    resp = client.post(
        "/api/v1/users",
        json={"full_name": "Dup", "username": "farmer1", "role": "farmer"},
        headers=headers,
    )
    assert resp.status_code == 409


def test_invitation_claim_links_telegram_and_delivers_temp_password(client, admin):
    headers = auth_headers(client, "admin1")
    resp = client.post(
        "/api/v1/users",
        json={"full_name": "Telegram User", "username": "tguser", "role": "farmer"},
        headers=headers,
    )
    code = resp.json()["invitation_code"]

    # bot claims through internal API
    claim = client.post(
        "/api/v1/internal/telegram/claim",
        json={"code": code, "telegram_id": "999888777", "telegram_username": "tguser_tg"},
        headers={"X-Internal-Secret": "test-internal-secret"},
    )
    assert claim.status_code == 200, claim.text
    payload = claim.json()
    assert payload["username"] == "tguser"
    assert payload["temporary_password"]

    # the temporary password actually works and forces a change
    tokens = login(client, "tguser", payload["temporary_password"])
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=h).json()
    assert me["must_change_password"] is True


def test_invitation_code_single_use(client, admin):
    headers = auth_headers(client, "admin1")
    resp = client.post(
        "/api/v1/users",
        json={"full_name": "Once", "username": "onceuser", "role": "farmer"},
        headers=headers,
    )
    code = resp.json()["invitation_code"]
    first = client.post(
        "/api/v1/internal/telegram/claim",
        json={"code": code, "telegram_id": "111222333"},
        headers={"X-Internal-Secret": "test-internal-secret"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/internal/telegram/claim",
        json={"code": code, "telegram_id": "555666777"},
        headers={"X-Internal-Secret": "test-internal-secret"},
    )
    assert second.status_code == 401


def test_invalid_invitation_code_rejected(client):
    resp = client.post(
        "/api/v1/internal/telegram/claim",
        json={"code": "TOTALLYBOGUS", "telegram_id": "12345"},
        headers={"X-Internal-Secret": "test-internal-secret"},
    )
    assert resp.status_code == 401


def test_internal_api_requires_secret(client):
    resp = client.post(
        "/api/v1/internal/telegram/claim",
        json={"code": "X", "telegram_id": "1"},
    )
    assert resp.status_code == 401


def test_admin_deactivate_and_activate(client, admin, farmer2):
    headers = auth_headers(client, "admin1")
    resp = client.post(f"/api/v1/users/{farmer2.id}/deactivate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    # deactivated user cannot log in
    assert client.post(
        "/api/v1/auth/login", json={"username": "farmer2", "password": "Password123!"}
    ).status_code == 401
    resp = client.post(f"/api/v1/users/{farmer2.id}/activate", headers=headers)
    assert resp.json()["is_active"] is True


def test_temp_password_endpoint(client, admin, farmer2):
    headers = auth_headers(client, "admin1")
    resp = client.post(f"/api/v1/users/{farmer2.id}/temporary-password", headers=headers)
    assert resp.status_code == 200
    temp = resp.json()["temporary_password"]
    assert client.post(
        "/api/v1/auth/login", json={"username": "farmer2", "password": temp}
    ).status_code == 200


def test_user_list_pagination_and_search(client, admin, farmer):
    headers = auth_headers(client, "admin1")
    resp = client.get("/api/v1/users?role=farmer&page=1&page_size=1", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1 and body["page_size"] == 1
    assert len(body["items"]) == 1
    resp = client.get("/api/v1/users?search=farmer1", headers=headers)
    assert any(u["username"] == "farmer1" for u in resp.json()["items"])


def test_profile_update_and_language(client, farmer):
    headers = auth_headers(client, "farmer1")
    resp = client.patch(
        "/api/v1/users/me", json={"preferred_language": "ru", "region": "Samarqand"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "ru"
    assert resp.json()["region"] == "Samarqand"
