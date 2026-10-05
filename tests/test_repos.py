from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "version" in response.json()

def test_get_repos():
    response = client.get("/repos/")
    # If DB is not populated or mocked, it should just return 200 with list
    assert response.status_code == 200
