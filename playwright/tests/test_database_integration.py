from datetime import date

from backend.app.db.database import SessionLocal
from backend.app.models import Transaction


def test_created_transaction_is_persisted_for_its_owner(client):
    registration = client.post(
        "/auth/register",
        json={
            "username": "db_user",
            "email": "db-user@example.com",
            "password": "secure-password",
        },
    )
    assert registration.status_code == 201
    token = client.post(
        "/auth/login",
        json={"email": "db-user@example.com", "password": "secure-password"},
    ).json()["access_token"]

    response = client.post(
        "/transactions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Persisted salary",
            "amount": 1250,
            "transaction_type": "Income",
            "category": "Salary",
            "transaction_date": "2026-01-15",
            "description": "Database integration test",
        },
    )

    assert response.status_code == 201
    transaction_id = response.json()["id"]
    with SessionLocal() as db:
        saved = db.query(Transaction).filter_by(id=transaction_id).one()
        assert saved.title == "Persisted salary"
        assert saved.amount == 1250
        assert saved.transaction_date == date(2026, 1, 15)
        assert saved.owner.email == "db-user@example.com"


def test_transaction_round_trips_through_the_api(client):
    client.post(
        "/auth/register",
        json={
            "username": "roundtrip_user",
            "email": "roundtrip@example.com",
            "password": "secure-password",
        },
    )
    token = client.post(
        "/auth/login",
        json={"email": "roundtrip@example.com", "password": "secure-password"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Coffee",
        "amount": 4.5,
        "transaction_type": "Expense",
        "category": "Food",
        "transaction_date": "2026-02-02",
    }

    created = client.post("/transactions", headers=headers, json=payload)
    listed = client.get("/transactions", headers=headers)

    assert created.status_code == 201
    assert any(item["id"] == created.json()["id"] for item in listed.json())
