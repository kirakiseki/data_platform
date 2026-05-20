"""Tests for /metadata/* endpoints."""


def test_date_range(client):
    r = client.get("/metadata/date-range")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["start_date"] == "2015-01-03"
    assert data["end_date"] is not None
    assert len(data["available_dates"]) > 0


def test_road_classes(client):
    r = client.get("/metadata/road-classes")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    item = body["data"][0]
    assert "class_id" in item
    assert "class_name" in item
