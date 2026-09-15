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
    # =========================
# STAGE 19 - AUTHORIZATION TESTS
# =========================

def test_user_cannot_update_ticket_status():
    def mock_user():
        return {
            "user_id": 1,
            "email": "user@example.com",
            "role": "USER"
        }

    app.dependency_overrides = {}

    from main import get_current_user
    app.dependency_overrides[get_current_user] = mock_user

    response = client.put(
        "/tickets/1/status?status=RESOLVED"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == \
        "You do not have permission to perform this action"

    app.dependency_overrides = {}


def test_agent_cannot_delete_ticket():
    def mock_user():
        return {
            "user_id": 2,
            "email": "agent@example.com",
            "role": "AGENT"
        }

    app.dependency_overrides = {}

    from main import get_current_user
    app.dependency_overrides[get_current_user] = mock_user

    response = client.delete("/tickets/1")

    assert response.status_code == 403
    assert response.json()["detail"] == \
        "You do not have permission to perform this action"

    app.dependency_overrides = {}


def test_user_cannot_delete_ticket():
    def mock_user():
        return {
            "user_id": 1,
            "email": "user@example.com",
            "role": "USER"
        }

    app.dependency_overrides = {}

    from main import get_current_user
    app.dependency_overrides[get_current_user] = mock_user

    response = client.delete("/tickets/1")

    assert response.status_code == 403
    assert response.json()["detail"] == \
        "You do not have permission to perform this action"

    app.dependency_overrides = {}