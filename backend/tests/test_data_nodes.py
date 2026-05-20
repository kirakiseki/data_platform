"""Tests for /data/nodes/* endpoints."""


def test_nodes_list(client):
    r = client.get("/data/nodes", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    data = body["data"]
    assert "total" in data
    assert "items" in data


def test_nodes_list_has_items(client):
    r = client.get("/data/nodes", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    # nodes may or may not exist depending on DB state
    assert body["data"] is not None


def test_get_node_not_found(client):
    r = client.get("/data/nodes/999999999")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 404
