from __future__ import annotations

from tests.conftest import auth_headers

BOUNDARY = {
    "type": "Polygon",
    "coordinates": [
        [[69.24, 41.31], [69.26, 41.31], [69.26, 41.33], [69.24, 41.33], [69.24, 41.31]]
    ],
}


def test_create_farm_with_boundary(client, farmer):
    resp = client.post(
        "/api/v1/farms",
        json={
            "name": "Xarita dalasi",
            "region": "Toshkent",
            "district": "Zangiota",
            "area_hectares": 12.5,
            "boundary": BOUNDARY,
            "center_lat": 41.32,
            "center_lng": 69.25,
        },
        headers=auth_headers(client, "farmer1"),
    )
    assert resp.status_code == 201, resp.text
    farm = resp.json()
    assert farm["boundary"] == BOUNDARY
    assert farm["center_lat"] == 41.32
    assert farm["center_lng"] == 69.25

    got = client.get(f"/api/v1/farms/{farm['id']}", headers=auth_headers(client, "farmer1")).json()
    assert got["boundary"] == BOUNDARY


def test_update_farm_boundary(client, farmer):
    h = auth_headers(client, "farmer1")
    farm = client.post(
        "/api/v1/farms",
        json={"name": "Dalacha", "region": "Samarqand", "district": "Kattaqo'rg'on"},
        headers=h,
    ).json()
    assert farm["boundary"] is None
    resp = client.patch(
        f"/api/v1/farms/{farm['id']}",
        json={"boundary": BOUNDARY, "center_lat": 41.32, "center_lng": 69.25},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["boundary"] == BOUNDARY


def test_other_farmer_cannot_draw_on_foreign_farm(client, farmer, farmer2):
    h1 = auth_headers(client, "farmer1")
    farm = client.post(
        "/api/v1/farms",
        json={"name": "X alm", "region": "Buxoro", "district": "Kogon"},
        headers=h1,
    ).json()
    resp = client.patch(
        f"/api/v1/farms/{farm['id']}",
        json={"boundary": BOUNDARY},
        headers=auth_headers(client, "farmer2"),
    )
    assert resp.status_code == 403
