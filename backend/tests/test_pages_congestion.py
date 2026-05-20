"""Tests for /page/congestion/roads/geojson endpoint."""

from conftest import TEST_DATE, TEST_HOUR


def test_congestion_geojson_basic(client):
    r = client.get(
        "/page/congestion/roads/geojson",
        params={"date": TEST_DATE, "hour": TEST_HOUR},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["type"] == "FeatureCollection"
    assert "features" in data


def test_congestion_geojson_feature_structure(client):
    r = client.get(
        "/page/congestion/roads/geojson",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "limit": 5},
    )
    body = r.json()
    features = body["data"]["features"]
    if features:
        f = features[0]
        assert f["type"] == "Feature"
        assert "geometry" in f
        assert "properties" in f
        props = f["properties"]
        assert "road_id" in props
        assert "status" in props
        assert "congestion_idx" in props


def test_congestion_geojson_default_filters_congested(client):
    # Without status filter, only 拥堵 and 严重拥堵 are returned
    r = client.get(
        "/page/congestion/roads/geojson",
        params={"date": TEST_DATE, "hour": TEST_HOUR},
    )
    body = r.json()
    for f in body["data"]["features"]:
        assert f["properties"]["status"] in ("拥堵", "严重拥堵")


def test_congestion_geojson_with_status_filter(client):
    r = client.get(
        "/page/congestion/roads/geojson",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "status": "缓行"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    for f in body["data"]["features"]:
        assert f["properties"]["status"] == "缓行"


def test_congestion_geojson_limit(client):
    r = client.get(
        "/page/congestion/roads/geojson",
        params={"date": TEST_DATE, "hour": TEST_HOUR, "limit": 3},
    )
    body = r.json()
    assert len(body["data"]["features"]) <= 3
