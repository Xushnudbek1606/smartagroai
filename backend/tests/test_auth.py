from __future__ import annotations

from tests.conftest import auth_headers, login, make_user


def test_login_success_and_me(client, farmer):
    tokens = login(client, "farmer1")
    assert "access_token" in tokens and "refresh_token" in tokens
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "farmer1"
    assert body["role"] == "farmer"


def test_login_wrong_password(client, farmer):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "farmer1", "password": "wrong-pass"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_user(client):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "ghost", "password": "whatever123"}
    )
    assert resp.status_code == 401


def test_inactive_user_cannot_login(client, db):
    make_user(db, "banned1", "farmer", is_active=False)
    resp = client.post(
        "/api/v1/auth/login", json={"username": "banned1", "password": "Password123!"}
    )
    assert resp.status_code == 401


def test_me_requires_token(client, farmer):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_token(client, farmer):
    tokens = login(client, "farmer1")
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    new_tokens = resp.json()
    # old refresh token must be unusable after rotation
    resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp2.status_code == 401
    # new one works
    resp3 = client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert resp3.status_code == 200


def test_logout_revokes_refresh_token(client, farmer):
    tokens = login(client, "farmer1")
    resp = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp2.status_code == 401


def test_change_password_flow(client, farmer):
    headers = auth_headers(client, "farmer1")
    # wrong current password
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "nope", "new_password": "NewPass123!"},
        headers=headers,
    )
    assert resp.status_code == 400
    # correct
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password123!", "new_password": "NewPass123!"},
        headers=headers,
    )
    assert resp.status_code == 200
    # old password no longer works, new one does
    assert client.post(
        "/api/v1/auth/login", json={"username": "farmer1", "password": "Password123!"}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"username": "farmer1", "password": "NewPass123!"}
    ).status_code == 200


def test_must_change_password_blocks_profile(client, db):
    make_user(db, "newguy", "farmer", must_change_password=True)
    tokens = login(client, "newguy")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    # /users/me blocked until password changed
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "password_change_required"
    # auth/me still accessible so the frontend can show the change-password page
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    # after change the block is lifted
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password123!", "new_password": "Changed123!"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/users/me", headers=headers).status_code == 200
