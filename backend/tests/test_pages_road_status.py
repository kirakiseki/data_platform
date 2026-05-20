"""Tests for /page/road-status endpoint."""

from conftest import TEST_DATE, TEST_HOUR


def test_road_status_page_basic(client):
    r = client.get(
        "/page/road-status",
        params={"date": TEST_DATE, "hour": TEST_HOUR},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "summary" in data
    assert "total" in data
    assert "items" in data
    assert "page" in data
    assert "page_size" in data


def test_road_status_summary_fields(client):
    r = client.get("/page/road-status", params={"date": TEST_DATE, "hour": TEST_HOUR})
    body = r.json()
    summary = body["data"]["summary"]
    assert "total_roads" in summary
    assert "congested_roads" in summary
    assert "severe_congested_roads" in summary


def test_road_status_item_fields(client):
    r = client.get(
        "/page/road-status",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page_size": 5},
    )
    body = r.json()
    items = body["data"]["items"]
    if items:
        item = items[0]
        assert "road_id" in item
        assert "status" in item


def test_road_status_filter_by_status(client):
    r = client.get(
        "/page/road-status",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "status": "拥堵"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    for item in body["data"]["items"]:
        assert item["status"] == "拥堵"


def test_road_status_pagination(client):
    r1 = client.get(
        "/page/road-status",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 1, "page_size": 5},
    )
    r2 = client.get(
        "/page/road-status",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "page": 2, "page_size": 5},
    )
    ids1 = {i["road_id"] for i in r1.json()["data"]["items"]}
    ids2 = {i["road_id"] for i in r2.json()["data"]["items"]}
    # Pages should not overlap
    assert ids1.isdisjoint(ids2)
