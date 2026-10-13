from __future__ import annotations

from tests.conftest import auth_headers


def test_farmer_creates_farm_and_crop(client, farmer):
    h = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/farms",
        json={"name": "Bog'", "region": "Farg'ona", "district": "Marg'ilon", "area_hectares": 12.5},
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    farm = resp.json()
    assert farm["name"] == "Bog'"
    assert farm["crops_count"] == 0

    resp = client.post(
        "/api/v1/crops",
        json={"farm_id": farm["id"], "name": "TOMATO", "variety": "Roma", "status": "growing"},
        headers=h,
    )
    assert resp.status_code == 201, resp.text
    crop = resp.json()
    assert crop["farm_name"] == "Bog'"

    # farm now reports crops_count=1
    resp = client.get(f"/api/v1/farms/{farm['id']}", headers=h)
    assert resp.json()["crops_count"] == 1

    # list crops filtered by farm
    resp = client.get(f"/api/v1/crops?farm_id={farm['id']}", headers=h)
    assert resp.json()["total"] == 1


def test_agronom_cannot_create_farm(client, agronom):
    h = auth_headers(client, "agronom1")
    resp = client.post(
        "/api/v1/farms",
        json={"name": "XX", "region": "XX", "district": "X"},
        headers=h,
    )
    assert resp.status_code == 403


def test_farmer_cannot_see_others_farm(client, farmer, farmer2, db):
    h1 = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/farms",
        json={"name": "Private", "region": "XX", "district": "X"},
        headers=h1,
    )
    farm_id = resp.json()["id"]
    h2 = auth_headers(client, "farmer2")
    assert client.get(f"/api/v1/farms/{farm_id}", headers=h2).status_code == 403
    assert client.patch(
        f"/api/v1/farms/{farm_id}", json={"name": "hacked"}, headers=h2
    ).status_code == 403
    assert client.delete(f"/api/v1/farms/{farm_id}", headers=h2).status_code == 403
    # list only shows own farms
    assert client.get("/api/v1/farms", headers=h2).json()["total"] == 0


def test_admin_sees_all_farms(client, farmer, admin):
    h1 = auth_headers(client, "farmer1")
    resp = client.post(
        "/api/v1/farms", json={"name": "Alpha", "region": "XX", "district": "X"}, headers=h1
    )
    assert resp.status_code == 201, resp.text
    ha = auth_headers(client, "admin1")
    assert client.get("/api/v1/farms", headers=ha).json()["total"] == 1


def test_update_and_delete_farm(client, farmer):
    h = auth_headers(client, "farmer1")
    farm = client.post(
        "/api/v1/farms", json={"name": "Old", "region": "XX", "district": "X"}, headers=h
    ).json()
    resp = client.patch(f"/api/v1/farms/{farm['id']}", json={"name": "New"}, headers=h)
    assert resp.json()["name"] == "New"
    assert client.delete(f"/api/v1/farms/{farm['id']}", headers=h).status_code == 204
    assert client.get(f"/api/v1/farms/{farm['id']}", headers=h).status_code == 404


def test_crop_validation(client, farmer):
    h = auth_headers(client, "farmer1")
    farm = client.post(
        "/api/v1/farms", json={"name": "FF", "region": "XX", "district": "X"}, headers=h
    ).json()
    # invalid status rejected by schema
    resp = client.post(
        "/api/v1/crops",
        json={"farm_id": farm["id"], "name": "Wheat", "status": "banana"},
        headers=h,
    )
    assert resp.status_code == 422
    # unknown farm rejected
    resp = client.post(
        "/api/v1/crops", json={"farm_id": "nope", "name": "Wheat"}, headers=h
    )
    assert resp.status_code == 404


def test_crop_update_status(client, farmer):
    h = auth_headers(client, "farmer1")
    farm = client.post(
        "/api/v1/farms", json={"name": "F2", "region": "XX", "district": "X"}, headers=h
    ).json()
    crop = client.post(
        "/api/v1/crops", json={"farm_id": farm["id"], "name": "Arpa"}, headers=h
    ).json()
    resp = client.patch(f"/api/v1/crops/{crop['id']}", json={"status": "harvested"}, headers=h)
    assert resp.json()["status"] == "harvested"
