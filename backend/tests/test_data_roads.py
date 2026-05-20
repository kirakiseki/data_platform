"""Tests for /data/roads/* endpoints."""

from conftest import TEST_DATE, TEST_HOUR


def test_road_status(client):
    r = client.get(
        "/data/roads/status",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_road_status_filter_by_status(client):
    r = client.get(
        "/data/roads/status",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "status": "拥堵"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_road_flow_daily(client):
    r = client.get(
        "/data/roads/flow/daily",
        params={"date": TEST_DATE, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert len(data["items"]) > 0
    item = data["items"][0]
    assert "road_id" in item


def test_road_travel_time(client):
    r = client.get(
        "/data/roads/travel-time",
        params={"date": TEST_DATE, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_road_geojson(client):
    r = client.get("/data/roads/geojson", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "features" in data
    assert len(data["features"]) > 0
    feature = data["features"][0]
    assert feature["type"] == "Feature"
    assert "geometry" in feature
    assert "properties" in feature
