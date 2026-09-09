import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_users():
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2


def test_create_valid_user():
    payload = {
        "username": "charlie",
        "email": "charlie@example.com",
        "role": "tester",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "charlie"
    assert data["email"] == "charlie@example.com"
