"""Tests for /data/od/* endpoints."""

from conftest import TEST_DATE, TEST_HOUR


def test_od_grid_hourly(client):
    r = client.get(
        "/data/od/grid/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_od_grid_daily(client):
    r = client.get(
        "/data/od/grid/daily",
        params={"date": TEST_DATE, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_od_cluster_hourly(client):
    r = client.get(
        "/data/od/cluster/hourly",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_od_cluster_daily(client):
    r = client.get(
        "/data/od/cluster/daily",
        params={"date": TEST_DATE, "page": 1, "page_size": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_od_cluster_daily_filter_flow(client):
    r = client.get(
        "/data/od/cluster/daily",
        params={"date": TEST_DATE, "flow_direction": "commute_outbound", "page": 1, "page_size": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
