def test_api_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_liveness_and_readiness(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").json()["status"] == "ready"
