def test_api_health_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "running" in response.json()["message"].lower()


def test_register_login_and_get_current_user(client):
    registration = client.post(
        "/auth/register",
        json={
            "username": "api_user",
            "email": "api-user@example.com",
            "password": "secure-password",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": "API-USER@example.com", "password": "secure-password"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    current_user = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "api-user@example.com"


def test_registration_rejects_duplicate_account(client):
    payload = {
        "username": "duplicate_user",
        "email": "duplicate@example.com",
        "password": "secure-password",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409
