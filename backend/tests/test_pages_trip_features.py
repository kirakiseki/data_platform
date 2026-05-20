"""Tests for /page/trip-features/od endpoint."""

from conftest import TEST_DATE


def test_trip_od_basic(client):
    r = client.get("/page/trip-features/od", params={"date": TEST_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "items" in data
    assert len(data["items"]) > 0


def test_trip_od_item_fields(client):
    r = client.get("/page/trip-features/od", params={"date": TEST_DATE, "top_n": 5})
    body = r.json()
    item = body["data"]["items"][0]
    assert "rank" in item
    assert item["rank"] == 1
    assert "origin_lon" in item
    assert "origin_lat" in item
    assert "dest_lon" in item
    assert "dest_lat" in item
    assert "trip_count" in item
    assert item["trip_count"] > 0


def test_trip_od_top_n(client):
    r = client.get("/page/trip-features/od", params={"date": TEST_DATE, "top_n": 3})
    body = r.json()
    assert len(body["data"]["items"]) <= 3


def test_trip_od_ranks_are_ordered(client):
    r = client.get("/page/trip-features/od", params={"date": TEST_DATE, "top_n": 5})
    items = r.json()["data"]["items"]
    ranks = [i["rank"] for i in items]
    assert ranks == sorted(ranks)


def test_trip_od_trip_counts_descending(client):
    r = client.get("/page/trip-features/od", params={"date": TEST_DATE, "top_n": 5})
    counts = [i["trip_count"] for i in r.json()["data"]["items"]]
    assert counts == sorted(counts, reverse=True)


def test_trip_od_filter_flow_direction(client):
    r = client.get(
        "/page/trip-features/od",
        params={"date": TEST_DATE, "flow_direction": "commute_outbound"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    for item in body["data"]["items"]:
        assert item["flow_direction"] == "commute_outbound"


def test_trip_od_avg_distance_in_km(client):
    r = client.get("/page/trip-features/od", params={"date": TEST_DATE, "top_n": 5})
    for item in r.json()["data"]["items"]:
        if item["avg_distance"] is not None:
            # avg_distance should be in km (service divides meters by 1000)
            assert item["avg_distance"] < 200  # no trip should average 200+ km
