"""Tests for /roads/* and /map/* endpoints."""


def test_roads_list(client):
    r = client.get("/roads", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["total"] > 0
    assert len(data["items"]) == 10
    item = data["items"][0]
    assert "gid" in item
    assert "class_id" in item
    assert "length" in item


def test_roads_list_filter_by_class(client):
    r = client.get("/roads", params={"page": 1, "page_size": 5, "class_id": 122})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_roads_stats(client):
    r = client.get("/roads/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["total_roads"] == 22304
    assert isinstance(data["by_class"], dict)


def test_get_road_by_gid(client):
    # First get a valid gid
    list_r = client.get("/roads", params={"page": 1, "page_size": 1})
    gid = list_r.json()["data"]["items"][0]["gid"]

    r = client.get(f"/roads/{gid}")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["gid"] == gid


def test_get_road_by_gid_not_found(client):
    r = client.get("/roads/999999999")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 404


def test_roads_geojson_all(client):
    r = client.get("/roads/geojson/all")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["type"] == "FeatureCollection"
    assert len(body["data"]["features"]) > 0


def test_roads_geojson_by_gid(client):
    list_r = client.get("/roads", params={"page": 1, "page_size": 1})
    gid = list_r.json()["data"]["items"][0]["gid"]

    r = client.get(f"/roads/geojson/{gid}")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["type"] == "Feature"


def test_roads_bbox_geojson(client):
    r = client.get(
        "/roads/geojson/all",
    )
    assert r.status_code == 200


def test_roads_bbox(client):
    r = client.get(
        "/roads/bbox/",
        params={
            "min_lng": 126.5,
            "min_lat": 45.7,
            "max_lng": 126.7,
            "max_lat": 45.8,
            "page": 1,
            "page_size": 10,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0


def test_map_data(client):
    r = client.get("/map/data")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]["roads"]) > 0
    road = body["data"]["roads"][0]
    assert "gid" in road
    assert "geom_json" in road
