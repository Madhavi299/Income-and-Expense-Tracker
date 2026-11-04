def test_login_keeps_missing_account_message_distinct(client):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "any-password"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Account not found. Please create an account first."
    )


def test_login_keeps_wrong_password_message_distinct(client):
    client.post(
        "/auth/register",
        json={
            "username": "regression_user",
            "email": "regression@example.com",
            "password": "secure-password",
        },
    )

    response = client.post(
        "/auth/login",
        json={"email": "regression@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect password. Please try again."


def test_transaction_validation_rejects_non_positive_amount(client):
    client.post(
        "/auth/register",
        json={
            "username": "validation_user",
            "email": "validation@example.com",
            "password": "secure-password",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": "validation@example.com", "password": "secure-password"},
    ).json()["access_token"]

    response = client.post(
        "/transactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Invalid amount",
            "amount": 0,
            "transaction_type": "Expense",
            "category": "Other",
            "transaction_date": "2026-03-01",
        },
    )

    assert response.status_code == 422
