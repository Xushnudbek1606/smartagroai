from __future__ import annotations

from tests.conftest import auth_headers

# 1x1 transparent PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _stub_ai(monkeypatch):
    from app.integrations.ai import AIResult, plant_ai_service

    monkeypatch.setattr(
        plant_ai_service,
        "analyze",
        lambda *a, **k: AIResult(None, None, None, "unknown"),
    )


def _subscription(client, username="farmer1"):
    return client.get(
        "/api/v1/users/me/subscription", headers=auth_headers(client, username)
    ).json()


def _diagnose(client):
    return client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
        headers=auth_headers(client, "farmer1"),
    )


def _start_conversation(client, agronom_id):
    return client.post(
        "/api/v1/conversations",
        json={"agronomist_id": agronom_id},
        headers=auth_headers(client, "farmer1"),
    )


def test_new_farmer_starts_with_full_free_quota(client, farmer):
    sub = _subscription(client)
    assert sub["plan"] == "free"
    assert sub["diagnoses_limit"] == 5
    assert sub["advice_limit"] == 5
    assert sub["diagnoses_remaining"] == 5
    assert sub["advice_remaining"] == 5
    assert sub["unlimited"] is False


def test_sixth_diagnosis_is_blocked_with_402(client, farmer, monkeypatch):
    _stub_ai(monkeypatch)
    h = auth_headers(client, "farmer1")
    for i in range(5):
        resp = _diagnose(client)
        assert resp.status_code == 201, f"diagnosis {i + 1} should succeed: {resp.text}"
    sub = _subscription(client)
    assert sub["diagnoses_used"] == 5
    assert sub["diagnoses_remaining"] == 0

    sixth = _diagnose(client)
    assert sixth.status_code == 402
    body = sixth.json()
    assert body["error"]["code"] == "subscription_required"
    assert body["error"]["details"]["feature"] == "diagnosis"


def test_sixth_advice_conversation_is_blocked_with_402(client, farmer, db, agronom):
    # 5 distinct agronomists: each new conversation consumes quota
    agronom_ids = []
    for i in range(5):
        from tests.conftest import make_user

        a = make_user(db, f"agronomQ{i}", "agronom")
        agronom_ids.append(a.id)
    for aid in agronom_ids:
        resp = _start_conversation(client, aid)
        assert resp.status_code == 201, resp.text
    sub = _subscription(client)
    assert sub["advice_used"] == 5
    assert sub["advice_remaining"] == 0

    sixth = _start_conversation(client, agronom.id)
    assert sixth.status_code == 402
    body = sixth.json()
    assert body["error"]["code"] == "subscription_required"
    assert body["error"]["details"]["feature"] == "advice"


def test_reopening_existing_conversation_is_free_after_limit(client, farmer, db, agronom):
    """The 402 paywall must not block reopening a conversation the farmer
    already has — only NEW conversations consume the quota."""
    agronom_ids = []
    for i in range(5):
        from tests.conftest import make_user

        a = make_user(db, f"agronomR{i}", "agronom")
        agronom_ids.append(a.id)
    for aid in agronom_ids:
        assert _start_conversation(client, aid).status_code == 201
    # quota exhausted now
    assert _start_conversation(client, agronom.id).status_code == 402
    # but an EXISTING conversation still opens (returns 200-shaped ConversationOut)
    resp = _start_conversation(client, agronom_ids[0])
    assert resp.status_code == 201, resp.text
    assert resp.json()["agronomist_id"] == agronom_ids[0]
    sub = _subscription(client)
    assert sub["advice_used"] == 5  # unchanged — reopened, not created


def test_admin_is_never_limited(client, admin, monkeypatch):
    _stub_ai(monkeypatch)
    h = auth_headers(client, "admin1")
    for _ in range(7):  # beyond the free limit
        resp = client.post(
            "/api/v1/diagnoses",
            files={"file": ("leaf.png", PNG_BYTES, "image/png")},
            data={"crop_type": "tomato"},
            headers=h,
        )
        assert resp.status_code == 201, resp.text
    sub = _subscription(client, "admin1")
    assert sub["unlimited"] is True
    assert sub["diagnoses_remaining"] is None


def test_deleting_diagnosis_does_not_return_quota(client, farmer, monkeypatch):
    """Counters are cumulative — delete must not unlock a free slot again."""
    _stub_ai(monkeypatch)
    h = auth_headers(client, "farmer1")
    ids = [_diagnose(client).json()["id"] for _ in range(5)]
    for did in ids:
        assert client.delete(f"/api/v1/diagnoses/{did}", headers=h).status_code == 204
    sub = _subscription(client)
    assert sub["diagnoses_used"] == 5
    assert _diagnose(client).status_code == 402


def test_existing_conversation_chatting_stays_free(client, farmer, db, agronom):
    """The limit applies to new conversations, not messages within one."""
    _start_conversation(client, agronom.id)
    conv_id = client.get(
        "/api/v1/conversations", headers=auth_headers(client, "farmer1")
    ).json()[0]["id"]
    h = auth_headers(client, "farmer1")
    for _ in range(10):
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/read", headers=h
        )  # any participant endpoint works
        assert resp.status_code == 200
    sub = _subscription(client)
    assert sub["advice_used"] == 1
    assert sub["advice_remaining"] == 4
