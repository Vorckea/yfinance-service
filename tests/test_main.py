from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_quote_invalid_symbol():
    response = client.get("/quote/INVALID$SYM")
    assert response.status_code == 400


def test_historical_invalid_symbol():
    response = client.get("/historical/INVALID$SYM")
    assert response.status_code == 400
