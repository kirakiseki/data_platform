"""Tests for /page/hotspot/zones endpoint."""

from conftest import TEST_DATE, TEST_HOUR


def _get_zones(client, zone_type, hour=None, page_size=10):
    params = {"zone_type": zone_type, "date": TEST_DATE, "page": 1, "page_size": page_size}
    if hour is not None:
        params["hour"] = hour
    return client.get("/page/hotspot/zones", params=params)


def test_hotspot_district_daily(client):
    r = _get_zones(client, "district")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) > 0


def test_hotspot_district_item_has_coords(client):
    r = _get_zones(client, "district")
    body = r.json()
    item = body["data"]["items"][0]
    assert "zone_id" in item
    assert "trip_count" in item
    assert "center_lon" in item
    assert "center_lat" in item
    # district zones should have centroid coords
    assert item["center_lon"] is not None
    assert item["center_lat"] is not None


def test_hotspot_district_hourly(client):
    r = _get_zones(client, "district", hour=TEST_HOUR)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) > 0


def test_hotspot_grid_daily(client):
    r = _get_zones(client, "grid")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_hotspot_poi_daily(client):
    r = _get_zones(client, "poi")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    if data["items"]:
        item = data["items"][0]
        assert "zone_id" in item
        assert "trip_count" in item


def test_hotspot_cluster_daily(client):
    r = _get_zones(client, "cluster")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    if data["items"]:
        item = data["items"][0]
        assert "center_lon" in item
        assert "center_lat" in item


def test_hotspot_cluster_hourly(client):
    r = _get_zones(client, "cluster", hour=TEST_HOUR)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_hotspot_pagination(client):
    r1 = _get_zones(client, "district", page_size=3)
    r2 = client.get(
        "/page/hotspot/zones",
        params={"zone_type": "district", "date": TEST_DATE, "page": 2, "page_size": 3},
    )
    ids1 = {i["zone_id"] for i in r1.json()["data"]["items"]}
    ids2 = {i["zone_id"] for i in r2.json()["data"]["items"]}
    assert ids1.isdisjoint(ids2)
