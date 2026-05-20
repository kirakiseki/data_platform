"""Tests for /data/tdm/* endpoints."""


def test_tdm_roads(client):
    r = client.get("/data/tdm/roads", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_tdm_nodes(client):
    r = client.get("/data/tdm/nodes", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_tdm_vehicles(client):
    r = client.get("/data/tdm/vehicles", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert len(data["items"]) > 0
    item = data["items"][0]
    assert "devid" in item


def test_tdm_vehicle_by_devid(client):
    # Get a valid devid first
    list_r = client.get("/data/tdm/vehicles", params={"page": 1, "page_size": 1})
    devid = list_r.json()["data"]["items"][0]["devid"]

    r = client.get(f"/data/tdm/vehicles/{devid}")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["devid"] == devid


def test_tdm_vehicle_not_found(client):
    r = client.get("/data/tdm/vehicles/nonexistent_devid_12345")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 404


def test_tdm_time_slots(client):
    r = client.get("/data/tdm/time-slots")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)


def test_tdm_districts(client):
    r = client.get("/data/tdm/districts")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    district = body["data"][0]
    assert "district_code" in district
    assert "district_name" in district
