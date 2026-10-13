from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers, make_user

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


def _sub(client, username):
    resp = client.get("/api/v1/users/me/subscription", headers=auth_headers(client, username))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _diagnose(client, username):
    return client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
        headers=auth_headers(client, username),
    )


def test_farmer_gets_farmer_defaults(client, farmer):
    sub = _sub(client, "farmer1")
    assert sub["role"] == "farmer"
    assert sub["plan"] == "free"
    assert sub["diagnoses_limit"] == 5
    assert sub["advice_limit"] == 5
    assert sub["diagnoses_remaining"] == 5
    assert sub["advice_remaining"] == 5
    assert sub["unlimited"] is False


def test_agronom_gets_agronom_defaults(client, agronom):
    sub = _sub(client, "agronom1")
    assert sub["role"] == "agronom"
    assert sub["diagnoses_limit"] == 30
    assert sub["diagnoses_remaining"] == 30
    # agronomists ANSWER advice: unlimited (-1)
    assert sub["advice_limit"] == -1
    assert sub["advice_remaining"] is None
    assert sub["unlimited"] is False  # diagnoses still limited
    # BUT: the paywall must never block an agronom from new conversations
    # (their advice quota is unlimited)


def test_agronom_can_start_many_conversations(client, agronom, db):
    from app.models import Conversation

    for i in range(3):
        f = make_user(db, f"farmerC{i}", "farmer")
        resp = client.post(
            "/api/v1/conversations",
            json={"agronomist_id": agronom.id},
            headers=auth_headers(client, f.username),
        )
        assert resp.status_code == 201, resp.text
    count = (
        db.query(Conversation).filter(Conversation.agronomist_id == agronom.id).count()
    )
    assert count == 3
    # agronom herself also participates; quota checks never 402 for advice


def test_agronom_diagnosis_quota_30(client, agronom, monkeypatch, db):
    """Agronom's diagnosis limit is 30 — far beyond a farmer's 5."""
    _stub_ai(monkeypatch)
    # simulate 29 used
    from app.services import subscription_service

    sub = subscription_service.ensure_subscription(db, agronom)
    sub.diagnoses_used = 29
    db.add(sub)
    db.commit()
    # 30th attempt: allowed
    ok = _diagnose(client, "agronom1")
    assert ok.status_code == 201, ok.text
    # 31st: blocked
    blocked = _diagnose(client, "agronom1")
    assert blocked.status_code == 402
    assert blocked.json()["error"]["details"]["feature"] == "diagnosis"


def test_admin_grants_pro_plan(client, admin, farmer):
    h = auth_headers(client, "admin1")
    resp = client.patch(
        f"/api/v1/users/{farmer.id}/subscription",
        json={"plan": "pro", "diagnoses_limit": 50, "advice_limit": 30},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["diagnoses_limit"] == 50
    assert body["advice_limit"] == 30
    # user sees her new plan
    sub = _sub(client, "farmer1")
    assert sub["plan"] == "pro"
    assert sub["diagnoses_limit"] == 50


def test_admin_grants_paid_until(client, admin, farmer):
    h = auth_headers(client, "admin1")
    until = datetime.now(timezone.utc) + timedelta(days=30)
    resp = client.patch(
        f"/api/v1/users/{farmer.id}/subscription",
        json={"plan": "pro", "paid_until": until.isoformat(), "reset_usage": True},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["paid_until"] is not None
    assert body["diagnoses_used"] == 0  # reset_usage worked


def test_admin_unlimited_flag(client, admin, farmer):
    h = auth_headers(client, "admin1")
    resp = client.patch(
        f"/api/v1/users/{farmer.id}/subscription",
        json={"advice_limit": -1, "diagnoses_limit": -1},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    sub = _sub(client, "farmer1")
    assert sub["advice_limit"] == -1
    assert sub["advice_remaining"] is None


def test_admin_cannot_edit_admin_subscription(client, admin):
    h = auth_headers(client, "admin1")
    resp = client.patch(
        f"/api/v1/users/{admin.id}/subscription",
        json={"diagnoses_limit": 3},
        headers=h,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "admin_unlimited"


def test_non_admin_cannot_manage_subscriptions(client, farmer):
    resp = client.get(
        f"/api/v1/users/{farmer.id}/subscription",
        headers=auth_headers(client, "farmer1"),
    )
    assert resp.status_code == 403


def test_admin_get_user_subscription(client, admin, agronom):
    h = auth_headers(client, "admin1")
    resp = client.get(f"/api/v1/users/{agronom.id}/subscription", headers=h)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "agronom"
    assert body["advice_limit"] == -1
    assert body["username"] == "agronom1"
