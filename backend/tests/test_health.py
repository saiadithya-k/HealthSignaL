from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert settings.PROJECT_NAME in data["message"]

def test_health_check_endpoint():
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data

def test_version_endpoint():
    response = client.get(f"{settings.API_V1_STR}/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == settings.VERSION
    assert data["min_group_size_default"] == 11
