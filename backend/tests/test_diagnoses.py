from __future__ import annotations

# 1x1 transparent PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_ai_not_configured_returns_503_not_fake_diagnosis(client, farmer):
    """When no AI provider is configured the API must clearly say so,
    never fabricate a diagnosis."""
    from tests.conftest import auth_headers

    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato", "region": "Farg'ona"},
        headers=h,
    )
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "ai_not_configured"


def test_integration_status_reports_unconfigured(client, farmer):
    from tests.conftest import auth_headers

    h = auth_headers(client, "farmer1")
    resp = client.get("/api/v1/diagnoses/integration-status", headers=h)
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


def test_upload_rejects_non_image(client, farmer):
    from tests.conftest import auth_headers

    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
        data={"crop_type": "tomato"},
        headers=h,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_file_type"


def test_upload_rejects_fake_content_type(client, farmer):
    """Client-sent MIME type is ignored; magic bytes decide."""
    from tests.conftest import auth_headers

    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", b"not an image at all", "image/png")},
        data={"crop_type": "tomato"},
        headers=h,
    )
    assert resp.status_code == 400


def test_upload_rejects_oversized_file(client, farmer, monkeypatch):
    from app.core.config import get_settings

    get_settings().UPLOAD_MAX_BYTES = 10
    from tests.conftest import auth_headers

    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
        headers=h,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "file_too_large"
    get_settings().UPLOAD_MAX_BYTES = 8 * 1024 * 1024


def test_agronom_diagnosis_quota_over_limit(client, agronom, db, monkeypatch):
    """Agronomists now get their own plan (30 diagnoses) — the check
    moves to quota enforcement instead of a blanket 403."""
    from tests.conftest import auth_headers

    from app.services import subscription_service

    sub = subscription_service.ensure_subscription(db, agronom)
    sub.diagnoses_used = sub.diagnoses_limit  # exhausted
    db.add(sub)
    db.commit()
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
        headers=auth_headers(client, "agronom1"),
    )
    assert resp.status_code == 402
    assert resp.json()["error"]["code"] == "subscription_required"


def test_diagnosis_requires_auth(client):
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
    )
    assert resp.status_code == 401


def test_diagnosis_with_mocked_ai_service(client, farmer, monkeypatch):
    """Full pipeline with a stubbed provider to verify persistence + access rules."""
    from app.integrations.ai import AIResult, plant_ai_service
    from tests.conftest import auth_headers

    def fake_analyze(image_path, *, crop_hint, region, language):
        return AIResult(
            predicted_crop="tomato",
            disease_name="Late blight",
            confidence=0.87,
            severity="high",
            symptoms=["leaf spots", "brown lesions"],
            recommendations=["remove affected leaves", "improve airflow"],
            next_steps="Consult an agronomist",
            model_version="test-stub-v1",
        )

    monkeypatch.setattr(plant_ai_service, "analyze", fake_analyze)
    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato", "region": "Farg'ona", "notes": "kechqurun paydo bo'ldi"},
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    diag = resp.json()
    assert diag["disease_name"] == "Late blight"
    assert diag["confidence"] == 0.87
    assert diag["model_version"] == "test-stub-v1"
    assert diag["image_url"].startswith("/static/plant_images/")
    assert diag["language"] == "uz-Latn"

    # stored in history and retrievable
    listed = client.get("/api/v1/diagnoses", headers=h).json()
    assert listed["total"] == 1
    got = client.get(f"/api/v1/diagnoses/{diag['id']}", headers=h)
    assert got.status_code == 200


def test_non_plant_image_saved_as_no_finding(client, farmer, monkeypatch):
    """An image with no visible plant/disease must be stored with
    status='no_finding' (not 'completed') so the UI can show a clear
    "retake the photo" warning instead of an "Unknown" diagnosis."""
    from app.integrations.ai import AIResult, plant_ai_service
    from tests.conftest import auth_headers

    monkeypatch.setattr(
        plant_ai_service,
        "analyze",
        lambda *a, **k: AIResult(
            predicted_crop=None,
            disease_name=None,
            confidence=None,
            severity="unknown",
            symptoms=[],
            recommendations=[],
            next_steps="Suratda o'simlik ko'rinmayapti, qayta oling.",
            model_version="test-stub-v1",
        ),
    )
    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/diagnoses",
        files={"file": ("gradient.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    diag = resp.json()
    assert diag["status"] == "no_finding"
    assert diag["disease_name"] is None
    assert diag["confidence"] is None
    # Still retrievable in history so the farmer sees the guidance.
    got = client.get(f"/api/v1/diagnoses/{diag['id']}", headers=h)
    assert got.status_code == 200


def test_other_farmer_cannot_read_diagnosis(client, farmer, farmer2, monkeypatch):
    from app.integrations.ai import AIResult, plant_ai_service
    from tests.conftest import auth_headers

    monkeypatch.setattr(
        plant_ai_service,
        "analyze",
        lambda *a, **k: AIResult(None, None, None, "unknown"),
    )
    h1 = auth_headers(client, "farmer1")
    diag = client.post(
        "/api/v1/diagnoses",
        files={"file": ("leaf.png", PNG_BYTES, "image/png")},
        data={"crop_type": "tomato"},
        headers=h1,
    ).json()
    h2 = auth_headers(client, "farmer2")
    assert client.get(f"/api/v1/diagnoses/{diag['id']}", headers=h2).status_code == 403
