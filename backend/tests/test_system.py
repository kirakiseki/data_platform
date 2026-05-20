"""Tests for system endpoints: root, heartbeat, version."""


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200


def test_heartbeat_returns_success(client):
    r = client.get("/heartbeat")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["health"] is True
    assert body["data"]["database"]["health"] is True


def test_version_returns_db_version(client):
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert "PostgreSQL" in body["data"]["database"]
