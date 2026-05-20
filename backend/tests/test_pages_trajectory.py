"""Tests for /page/trajectory/* endpoints."""

from conftest import TEST_DATE, TEST_HOUR


def test_trajectory_daily_stats(client):
    r = client.get("/page/trajectory/daily-stats")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    assert len(data["items"]) > 0


def test_trajectory_daily_stats_item_fields(client):
    r = client.get("/page/trajectory/daily-stats")
    item = r.json()["data"]["items"][0]
    assert "stat_date" in item
    assert "trips" in item
    assert "total_vehicles" in item
    assert "avg_speed" in item
    # GPS point counts come from ODS layer
    assert "total_gps_points" in item
    assert "total_matched_roads" in item


def test_trajectory_daily_stats_first_date(client):
    r = client.get("/page/trajectory/daily-stats")
    items = r.json()["data"]["items"]
    assert items[0]["stat_date"] == "2015-01-03"


def test_trajectory_samples_no_filter(client):
    r = client.get("/page/trajectory/samples", params={"sample_size": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    assert len(data["items"]) <= 3


def test_trajectory_samples_item_fields(client):
    r = client.get("/page/trajectory/samples", params={"sample_size": 1})
    body = r.json()
    items = body["data"]["items"]
    if items:
        item = items[0]
        assert "trip_id" in item
        assert "devid" in item
        assert "trip_date" in item
        assert "total_distance_m" in item
        assert "duration_s" in item
        assert "route_line" in item


def test_trajectory_samples_with_date(client):
    r = client.get(
        "/page/trajectory/samples",
        params={"date": TEST_DATE, "sample_size": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    for item in body["data"]["items"]:
        assert item["trip_date"] == TEST_DATE


def test_trajectory_samples_with_date_and_hour(client):
    r = client.get(
        "/page/trajectory/samples",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "sample_size": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    for item in body["data"]["items"]:
        assert item["start_hour"] == TEST_HOUR


def test_trajectory_samples_route_line_is_geojson(client):
    r = client.get("/page/trajectory/samples", params={"sample_size": 5})
    for item in r.json()["data"]["items"]:
        if item["route_line"] is not None:
            geom = item["route_line"]
            assert geom["type"] in ("LineString", "MultiLineString")
            assert "coordinates" in geom
