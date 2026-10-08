from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    print("Health check response:", response.json())

if __name__ == "__main__":
    test_health()
