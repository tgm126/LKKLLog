def test_health(client, db):
    odpoved = client.get("/api/health")
    assert odpoved.status_code == 200
    assert odpoved.json() == {"status": "ok", "databaze": True, "verze": "dev"}
