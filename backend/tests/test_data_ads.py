"""Tests for /data/ads/* endpoints."""

from conftest import TEST_DATE, TEST_HOUR


def test_network_status_hourly(client):
    r = client.get("/data/ads/network-status/hourly", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_congestion_hourly(client):
    r = client.get("/data/ads/congestion/hourly", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_top_congested_roads(client):
    r = client.get(
        "/data/ads/top-congested-roads",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "limit": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_trips_distance_hourly(client):
    r = client.get("/data/ads/trips/distance/hourly", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_trips_distance_daily(client):
    r = client.get("/data/ads/trips/distance/daily")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) > 0


def test_trips_speed_hourly(client):
    r = client.get("/data/ads/trips/speed/hourly", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_trips_speed_daily(client):
    r = client.get("/data/ads/trips/speed/daily")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) > 0


def test_trips_timeslot_daily(client):
    r = client.get("/data/ads/trips/timeslot/daily")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_hotspots_monitor_daily(client):
    r = client.get("/data/ads/hotspots/monitor/daily", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_road_status_hourly(client):
    r = client.get(
        "/data/ads/roads/status/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_hotspots_district_hourly(client):
    r = client.get(
        "/data/ads/hotspots/district/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_hotspots_district_daily(client):
    r = client.get("/data/ads/hotspots/district/daily", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_hotspots_grid_hourly(client):
    r = client.get(
        "/data/ads/hotspots/grid/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_hotspots_grid_daily(client):
    r = client.get(
        "/data/ads/hotspots/grid/daily",
        params={"date": TEST_DATE, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_hotspots_cluster_hourly(client):
    r = client.get(
        "/data/ads/hotspots/cluster/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_hotspots_cluster_daily(client):
    r = client.get(
        "/data/ads/hotspots/cluster/daily",
        params={"date": TEST_DATE, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_hotspots_poi_hourly(client):
    r = client.get(
        "/data/ads/hotspots/poi/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]


def test_hotspots_poi_daily(client):
    r = client.get("/data/ads/hotspots/poi/daily", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "items" in body["data"]
