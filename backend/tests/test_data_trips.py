"""Tests for /data/trips/* endpoints."""

from conftest import TEST_DATE


def test_trips_list(client):
    r = client.get("/data/trips", params={"date": TEST_DATE, "page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["total"] > 0
    assert len(data["items"]) == 10
    item = data["items"][0]
    assert "trip_id" in item
    assert "devid" in item
    assert "total_distance_m" in item


def test_trips_list_no_date(client):
    r = client.get("/data/trips", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["total"] > 0


def test_trips_list_filter_long_trip(client):
    r = client.get(
        "/data/trips",
        params={"date": TEST_DATE, "is_long_trip": True, "page": 1, "page_size": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_get_trip_detail(client):
    # Get a valid trip_id first
    list_r = client.get("/data/trips", params={"date": TEST_DATE, "page": 1, "page_size": 1})
    trip_id = list_r.json()["data"]["items"][0]["trip_id"]

    r = client.get(f"/data/trips/{trip_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["data"]["trip_id"] == trip_id


def test_get_trip_detail_not_found(client):
    r = client.get("/data/trips/999999999")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 404


def test_gps_points(client):
    list_r = client.get("/data/trips", params={"date": TEST_DATE, "page": 1, "page_size": 1})
    trip_id = list_r.json()["data"]["items"][0]["trip_id"]

    r = client.get("/data/trips/gps-points", params={"trip_id": trip_id})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["trip_id"] == trip_id
    assert len(data["items"]) > 0
    pt = data["items"][0]
    assert "lon" in pt
    assert "lat" in pt
