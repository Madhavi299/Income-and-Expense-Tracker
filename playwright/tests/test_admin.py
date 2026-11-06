from sqlalchemy import create_engine, inspect, text

from backend.app import main
from backend.app.db.database import SessionLocal, initialize_database
from backend.app.models import ActivityLog, User


def _register(client, username, email):
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "secure-password",
        },
    )
    assert response.status_code == 201
    return response.json()


def _login(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "secure-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _promote(user_id):
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).one()
        user.role = "admin"
        db.commit()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_regular_user_cannot_access_admin_or_transaction_admin_routes(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "regular_user",
            "email": "regular@example.com",
            "password": "secure-password",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    user = response.json()
    token = _login(client, user["email"])

    assert user["role"] == "user"
    assert user["is_active"] is True
    assert client.get("/admin/users", headers=_headers(token)).status_code == 403
    assert client.get("/transactions", headers=_headers(token)).status_code == 200


def test_admin_manages_users_and_deactivated_user_loses_access(client):
    admin = _register(client, "site_admin", "admin@example.com")
    target = _register(client, "managed_user", "managed@example.com")
    _promote(admin["id"])
    admin_token = _login(client, admin["email"])
    target_token = _login(client, target["email"])

    assert client.get("/transactions", headers=_headers(admin_token)).status_code == 403
    listed = client.get("/admin/users", headers=_headers(admin_token))
    assert listed.status_code == 200
    assert {user["email"] for user in listed.json()} >= {
        admin["email"],
        target["email"],
    }

    promoted = client.patch(
        f"/admin/users/{target['id']}",
        headers=_headers(admin_token),
        json={"role": "admin"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"

    deactivated = client.patch(
        f"/admin/users/{target['id']}",
        headers=_headers(admin_token),
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.get("/transactions", headers=_headers(target_token)).status_code == 403
    assert (
        client.post(
            "/auth/login",
            json={"email": target["email"], "password": "secure-password"},
        ).status_code
        == 403
    )

    activity = client.get("/admin/activity", headers=_headers(admin_token))
    assert activity.status_code == 200
    actions = {event["action"] for event in activity.json()}
    assert "user_registered" in actions
    assert "login_succeeded" in actions
    assert "user_account_updated" in actions
    assert "login_blocked_inactive" in actions


def test_admin_user_list_shows_only_transaction_totals(client):
    admin = _register(client, "totals_admin", "totals-admin@example.com")
    target = _register(client, "totals_user", "totals-user@example.com")
    _promote(admin["id"])
    admin_token = _login(client, admin["email"])
    target_token = _login(client, target["email"])

    for transaction_type, amount, title in (
        ("Income", 1200, "salary"),
        ("Expense", 450, "groceries"),
    ):
        response = client.post(
            "/transactions",
            headers=_headers(target_token),
            json={
                "title": title,
                "amount": amount,
                "transaction_type": transaction_type,
                "transaction_date": "2026-11-06",
            },
        )
        assert response.status_code == 201

    listed = client.get("/admin/users", headers=_headers(admin_token))
    assert listed.status_code == 200
    target_summary = next(
        user for user in listed.json() if user["id"] == target["id"]
    )
    assert target_summary["total_income"] == 1200
    assert target_summary["total_expenses"] == 450
    assert target_summary["balance"] == 750
    assert "transactions" not in target_summary
    assert "title" not in target_summary
    assert "transaction_type" not in target_summary


def test_admin_cannot_modify_own_access_and_demoted_admin_loses_access(client):
    first_admin = _register(client, "first_admin", "first-admin@example.com")
    second_admin = _register(client, "second_admin", "second-admin@example.com")
    _promote(first_admin["id"])
    _promote(second_admin["id"])
    first_token = _login(client, first_admin["email"])
    second_token = _login(client, second_admin["email"])

    self_change = client.patch(
        f"/admin/users/{first_admin['id']}",
        headers=_headers(first_token),
        json={"is_active": False},
    )
    assert self_change.status_code == 400

    demote_other = client.patch(
        f"/admin/users/{second_admin['id']}",
        headers=_headers(first_token),
        json={"role": "user"},
    )
    assert demote_other.status_code == 200
    assert client.get("/admin/users", headers=_headers(second_token)).status_code == 403


def test_initial_admin_bootstrap_creates_admin_and_does_not_reset_password(
    client, monkeypatch
):
    monkeypatch.setattr(main, "INITIAL_ADMIN_EMAIL", "first-admin@example.com")
    monkeypatch.setattr(main, "INITIAL_ADMIN_PASSWORD", "bootstrap-password")
    monkeypatch.setattr(main, "INITIAL_ADMIN_USERNAME", "bootstrap_admin")

    main.ensure_initial_admin()
    monkeypatch.setattr(main, "INITIAL_ADMIN_PASSWORD", "changed-password")
    main.ensure_initial_admin()

    response = client.post(
        "/auth/login",
        json={
            "email": "first-admin@example.com",
            "password": "bootstrap-password",
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"
    assert (
        client.post(
            "/auth/login",
            json={
                "email": "first-admin@example.com",
                "password": "changed-password",
            },
        ).status_code
        == 401
    )

    with SessionLocal() as db:
        db.query(User).filter(User.id == response.json()["user"]["id"]).update(
            {"role": "user"}
        )
        db.commit()
    main.ensure_initial_admin()
    with SessionLocal() as db:
        bootstrapped_user = (
            db.query(User)
            .filter(User.email == "first-admin@example.com")
            .one()
        )
        assert bootstrapped_user.role == "user"


def test_existing_regular_account_is_not_promoted_by_admin_bootstrap(
    client, monkeypatch
):
    user = _register(client, "existing_user", "existing@example.com")
    monkeypatch.setattr(main, "INITIAL_ADMIN_EMAIL", user["email"])
    monkeypatch.setattr(main, "INITIAL_ADMIN_PASSWORD", "bootstrap-password")
    monkeypatch.setattr(main, "INITIAL_ADMIN_USERNAME", "bootstrap_admin")
    monkeypatch.setattr(main, "INITIAL_ADMIN_PROMOTE_EXISTING", False)

    try:
        main.ensure_initial_admin()
    except RuntimeError as exc:
        assert "already belongs to a non-admin account" in str(exc)
    else:
        raise AssertionError("Bootstrap must not promote an existing regular user")


def test_admin_bootstrap_can_explicitly_promote_existing_account(client, monkeypatch):
    user = _register(client, "existing_admin", "existing-admin@example.com")
    monkeypatch.setattr(main, "INITIAL_ADMIN_EMAIL", user["email"])
    monkeypatch.setattr(main, "INITIAL_ADMIN_PASSWORD", "configured-password")
    monkeypatch.setattr(main, "INITIAL_ADMIN_USERNAME", "bootstrap_admin")
    monkeypatch.setattr(main, "INITIAL_ADMIN_PROMOTE_EXISTING", True)

    main.ensure_initial_admin()

    token = _login(client, user["email"])
    me = client.get("/auth/me", headers=_headers(token))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert client.get("/admin/users", headers=_headers(token)).status_code == 200

    with SessionLocal() as db:
        db.query(User).filter(User.id == user["id"]).update({"role": "user"})
        db.commit()
    main.ensure_initial_admin()
    with SessionLocal() as db:
        assert db.query(User).filter(User.id == user["id"]).one().role == "user"

    with SessionLocal() as db:
        log_entry = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.action == "initial_admin_promoted",
                ActivityLog.target_user_id == user["id"],
            )
            .one()
        )
        assert log_entry.actor_user_id is None


def test_existing_database_gets_role_columns_without_losing_users(tmp_path):
    database_path = (tmp_path / "legacy.db").as_posix()
    legacy_engine = create_engine(f"sqlite:///{database_path}")
    try:
        with legacy_engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE users ("
                    "id INTEGER PRIMARY KEY, "
                    "username VARCHAR(80) NOT NULL, "
                    "email VARCHAR(255) NOT NULL, "
                    "password_hash VARCHAR(255) NOT NULL, "
                    "created_at DATETIME)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, username, email, password_hash) "
                    "VALUES (1, 'legacy', 'legacy@example.com', 'hash')"
                )
            )

        initialize_database(legacy_engine)

        columns = {column["name"] for column in inspect(legacy_engine).get_columns("users")}
        assert {"role", "is_active"} <= columns
        with legacy_engine.connect() as connection:
            user = connection.execute(
                text("SELECT username, role, is_active FROM users WHERE id = 1")
            ).one()
        assert user.username == "legacy"
        assert user.role == "user"
        assert bool(user.is_active)
    finally:
        legacy_engine.dispose()
