from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Helpdesk Ticket Management System API is running"
    )


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"


def test_login_success():
    response = client.post(
        "/login",
        json={
            "email": "testuser@example.com",
            "password": "Test@1234"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Login successful"
    assert data["token_type"] == "bearer"
    assert "access_token" in data


def test_login_invalid_password():
    response = client.post(
        "/login",
        json={
            "email": "testuser@example.com",
            "password": "WrongPassword123"
        }
    )

    assert response.status_code == 401


def test_tickets_without_token():
    response = client.get("/tickets")

    assert response.status_code == 401


def test_get_tickets_with_token():
    login_response = client.post(
        "/login",
        json={
            "email": "testuser@example.com",
            "password": "Test@1234"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/tickets",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200
    assert "tickets" in response.json()


def test_invalid_ticket():
    login_response = client.post(
        "/login",
        json={
            "email": "testuser@example.com",
            "password": "Test@1234"
        }
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/tickets/999999",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 404