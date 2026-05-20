"""Tests for /page/dashboard endpoint."""

from conftest import TEST_DATE, TEST_HOUR


def test_dashboard_basic(client):
    r = client.get("/page/dashboard", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "platform_stats" in data
    assert "day_stats" in data
    assert "network_trend" in data
    assert "distance_trend" in data
    assert "top_roads" in data
    assert "top_hotspots" in data


def test_dashboard_platform_stats(client):
    r = client.get("/page/dashboard", params={"date": TEST_DATE})
    body = r.json()
    stats = body["data"]["platform_stats"]
    assert stats["total_trips"] > 0
    assert stats["total_vehicles"] > 0
    assert stats["road_segments"] == 22304


def test_dashboard_with_hour(client):
    r = client.get("/page/dashboard", params={"date": TEST_DATE, "hour": TEST_HOUR})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    # hour_stats should be populated when hour is given
    assert data["hour_stats"] is not None
    assert "trips" in data["hour_stats"]


def test_dashboard_without_hour_no_hour_stats(client):
    r = client.get("/page/dashboard", params={"date": TEST_DATE})
    body = r.json()
    assert body["data"]["hour_stats"] is None


def test_dashboard_top_n(client):
    r = client.get("/page/dashboard", params={"date": TEST_DATE, "top_n": 3})
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]["top_roads"]) <= 3
    assert len(body["data"]["top_hotspots"]) <= 3


def test_dashboard_network_trend_has_hour_items(client):
    r = client.get("/page/dashboard", params={"date": TEST_DATE})
    body = r.json()
    trend = body["data"]["network_trend"]
    assert len(trend) > 0
    item = trend[0]
    assert "hour" in item
    assert "avg_speed" in item
