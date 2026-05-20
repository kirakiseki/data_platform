"""Tests for /data/network/* endpoints."""

from conftest import TEST_DATE, TEST_HOUR


def test_network_daily(client):
    r = client.get("/data/network/daily")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    items = body["data"]["items"]
    assert len(items) > 0
    item = items[0]
    assert "stat_date" in item
    assert "total_trips" in item
    assert "network_avg_speed" in item


def test_network_hourly(client):
    r = client.get("/data/network/hourly", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["date"] == TEST_DATE
    items = body["data"]["items"]
    assert len(items) > 0
    item = items[0]
    assert "hour" in item
    assert "total_trips" in item


def test_network_summary_all(client):
    r = client.get("/data/network/summary", params={"time_mode": "all"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["total_trips"] is not None


def test_network_summary_day(client):
    r = client.get("/data/network/summary", params={"time_mode": "day", "date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["total_trips"] is not None


def test_network_summary_hour(client):
    r = client.get(
        "/data/network/summary",
        params={"time_mode": "hour", "date": TEST_DATE, "hour": TEST_HOUR},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"] is not None


def test_network_summary_day_missing_date(client):
    r = client.get("/data/network/summary", params={"time_mode": "day"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 400


def test_network_summary_hour_missing_hour(client):
    r = client.get(
        "/data/network/summary", params={"time_mode": "hour", "date": TEST_DATE}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 400
