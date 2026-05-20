"""Tests for /data/poi/* endpoints."""

from conftest import TEST_DATE, TEST_HOUR


def test_poi_flow_hourly(client):
    r = client.get("/data/poi/flow/hourly", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    assert "total" in data


def test_poi_flow_hourly_with_hour(client):
    r = client.get("/data/poi/flow/hourly", params={"date": TEST_DATE, "hour": TEST_HOUR})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_poi_flow_daily(client):
    r = client.get("/data/poi/flow/daily", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    assert "total" in data
