def _create_user(client, username, email):
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "secure-password",
        },
    )
    assert response.status_code == 201
    return client.post(
        "/auth/login",
        json={"email": email, "password": "secure-password"},
    ).json()["access_token"]


def test_transactions_require_authentication(client):
    response = client.get("/transactions")

    assert response.status_code == 401


def test_user_cannot_read_or_modify_another_users_transaction(client):
    owner_token = _create_user(client, "owner_user", "owner@example.com")
    other_token = _create_user(client, "other_user", "other@example.com")
    transaction = client.post(
        "/transactions",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "title": "Private record",
            "amount": 100,
            "transaction_type": "Expense",
            "category": "Other",
            "transaction_date": "2026-04-01",
        },
    )
    assert transaction.status_code == 201
    transaction_id = transaction.json()["id"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.get("/transactions", headers=other_headers).json() == []
    assert (
        client.patch(
            f"/transactions/{transaction_id}",
            headers=other_headers,
            json={"title": "Unauthorized edit"},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/transactions/{transaction_id}", headers=other_headers
        ).status_code
        == 404
    )


def test_failed_login_does_not_issue_an_access_token(client):
    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )

    assert response.status_code in {401, 404}
    assert "access_token" not in response.json()
