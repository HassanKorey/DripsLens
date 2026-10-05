from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_issues():
    response = client.get("/issues/")
    assert response.status_code == 200
