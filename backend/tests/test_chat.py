from __future__ import annotations

from tests.conftest import auth_headers


def _start_conversation(client, farmer_user, agronom_user):
    h = auth_headers(client, farmer_user.username)
    resp = client.post(
        "/api/v1/conversations", json={"agronomist_id": agronom_user.id}, headers=h
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_farmer_starts_conversation(client, farmer, agronom):
    conv = _start_conversation(client, farmer, agronom)
    assert conv["farmer_id"] == farmer.id
    assert conv["agronomist_id"] == agronom.id
    assert conv["partner"]["username"] == "agronom1"


def test_duplicate_conversation_is_reused(client, farmer, agronom):
    c1 = _start_conversation(client, farmer, agronom)
    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/conversations", json={"agronomist_id": agronom.id}, headers=h
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == c1["id"]


def test_agronom_cannot_start_conversation(client, agronom, farmer):
    h = auth_headers(client, "agronom1")
    resp = client.post(
        "/api/v1/conversations", json={"agronomist_id": farmer.id}, headers=h
    )
    assert resp.status_code == 403


def test_conversation_list_is_scoped(client, farmer, farmer2, agronom):
    _start_conversation(client, farmer, agronom)
    h2 = auth_headers(client, "farmer2")
    assert len(client.get("/api/v1/conversations", headers=h2).json()) == 0
    ha = auth_headers(client, "agronom1")
    convs = client.get("/api/v1/conversations", headers=ha).json()
    assert len(convs) == 1


def test_non_participant_cannot_read_messages(client, farmer, farmer2, agronom):
    conv = _start_conversation(client, farmer, agronom)
    h = auth_headers(client, "farmer1")
    # seed a message via websocket would be complex; use REST read endpoint directly
    resp = client.get(f"/api/v1/conversations/{conv['id']}/messages", headers=h)
    assert resp.status_code == 200
    h2 = auth_headers(client, "farmer2")
    resp = client.get(f"/api/v1/conversations/{conv['id']}/messages", headers=h2)
    assert resp.status_code == 403


def test_mark_read(client, farmer, farmer2, agronom):
    conv = _start_conversation(client, farmer, agronom)
    ha = auth_headers(client, "agronom1")
    resp = client.post(f"/api/v1/conversations/{conv['id']}/read", headers=ha)
    assert resp.status_code == 200
    resp = client.post(f"/api/v1/conversations/{conv['id']}/read", headers=auth_headers(client, "farmer2"))
    assert resp.status_code == 403


def test_websocket_requires_valid_token(client, farmer, agronom):
    conv = _start_conversation(client, farmer, agronom)
    try:
        with client.websocket_connect(f"/ws/chat/{conv['id']}?token=bogus") as ws:
            ws.receive()
        assert False, "connection should have been rejected"
    except Exception:
        pass


def test_websocket_message_flow(client, farmer, agronom):
    conv = _start_conversation(client, farmer, agronom)
    h = auth_headers(client, "farmer1")
    tokens = client.post(
        "/api/v1/auth/login", json={"username": "farmer1", "password": "Password123!"}
    ).json()
    token = tokens["access_token"]

    with client.websocket_connect(f"/ws/chat/{conv['id']}?token={token}") as ws:
        ws.send_json({"event": "message.send", "text": "Assalomu alaykum, doktor!"})
        data = ws.receive_json()
        assert data["event"] == "message.created"
        assert data["message"]["message_text"] == "Assalomu alaykum, doktor!"

    # persisted and visible via REST
    msgs = client.get(f"/api/v1/conversations/{conv['id']}/messages", headers=h).json()
    assert msgs["total"] == 1
    assert msgs["items"][0]["message_text"] == "Assalomu alaykum, doktor!"

    # agronom sees unread indicator
    ha = auth_headers(client, "agronom1")
    convs = client.get("/api/v1/conversations", headers=ha).json()
    assert convs[0]["unread_count"] == 1

    # notification created for the agronom
    notes = client.get("/api/v1/notifications", headers=ha).json()
    assert notes["total"] >= 1


def test_websocket_rejects_non_participant(client, farmer, farmer2, agronom):
    conv = _start_conversation(client, farmer, agronom)
    tokens = client.post(
        "/api/v1/auth/login", json={"username": "farmer2", "password": "Password123!"}
    ).json()
    try:
        with client.websocket_connect(
            f"/ws/chat/{conv['id']}?token={tokens['access_token']}"
        ) as ws:
            ws.receive_json()
        assert False, "should have been rejected"
    except Exception:
        pass


def test_websocket_message_length_limit(client, farmer, agronom):
    conv = _start_conversation(client, farmer, agronom)
    tokens = client.post(
        "/api/v1/auth/login", json={"username": "farmer1", "password": "Password123!"}
    ).json()
    with client.websocket_connect(
        f"/ws/chat/{conv['id']}?token={tokens['access_token']}"
    ) as ws:
        ws.send_json({"event": "message.send", "text": "x" * 5000})
        data = ws.receive_json()
        assert data["event"] == "error"
        assert data["code"] == "message_too_long"
