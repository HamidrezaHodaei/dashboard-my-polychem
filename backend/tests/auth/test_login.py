"""POST /api/auth/login tests."""
from app.core.audit_logs.models import AuditLog
from app.extensions import db

from .factories import login, make_user


def test_login_success_with_username(client, app):
    make_user(username="alice", email="alice@example.com")

    response = login(client, "alice")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["user"]["username"] == "alice"
    assert "access_token" in body["data"]
    assert "password_hash" not in body["data"]["user"]
    assert "refresh_token" not in body["data"]  # never returned in JSON

    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(h.startswith("refresh_token=") for h in set_cookie_headers)
    assert any("HttpOnly" in h for h in set_cookie_headers)
    assert any("SameSite=Strict" in h for h in set_cookie_headers)


def test_login_success_with_email(client, app):
    make_user(username="bob", email="bob@example.com")

    response = login(client, "bob@example.com")

    assert response.status_code == 200
    assert response.get_json()["data"]["user"]["username"] == "bob"


def test_login_wrong_password(client, app):
    make_user(username="carol", email="carol@example.com")

    response = client.post(
        "/api/auth/login", json={"identifier": "carol", "password": "totally-wrong"}
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "AUTHENTICATION_ERROR"
    assert response.get_json()["error"]["message"] == "Invalid credentials."


def test_login_unknown_identifier(client, app):
    response = client.post(
        "/api/auth/login", json={"identifier": "nobody-here", "password": "whatever123"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["message"] == "Invalid credentials."


def test_login_inactive_user(client, app):
    make_user(username="dave", email="dave@example.com", is_active=False)

    response = login(client, "dave")

    assert response.status_code == 401
    assert response.get_json()["error"]["message"] == "Invalid credentials."


def test_login_soft_deleted_user(client, app):
    from datetime import datetime, timezone

    user = make_user(username="erin", email="erin@example.com")
    user.deleted_at = datetime.now(timezone.utc)
    db.session.commit()

    response = login(client, "erin")

    assert response.status_code == 401
    assert response.get_json()["error"]["message"] == "Invalid credentials."


def test_login_missing_identifier(client, app):
    response = client.post("/api/auth/login", json={"password": "whatever123"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_missing_password(client, app):
    response = client.post("/api/auth/login", json={"identifier": "someone"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_no_user_enumeration_identical_error(client, app):
    make_user(username="frank", email="frank@example.com")

    wrong_password = client.post(
        "/api/auth/login", json={"identifier": "frank", "password": "wrong-one"}
    )
    unknown_identifier = client.post(
        "/api/auth/login", json={"identifier": "nobody", "password": "wrong-one"}
    )

    assert wrong_password.status_code == unknown_identifier.status_code == 401
    assert wrong_password.get_json()["error"] == unknown_identifier.get_json()["error"]


def test_login_updates_last_login_at(client, app):
    user = make_user(username="grace", email="grace@example.com")
    assert user.last_login_at is None

    login(client, "grace")

    db.session.refresh(user)
    assert user.last_login_at is not None


def test_login_success_writes_audit_event(client, app):
    make_user(username="hank", email="hank@example.com")

    login(client, "hank")

    events = db.session.query(AuditLog).filter_by(action="login_success").all()
    assert len(events) == 1
    assert events[0].module == "auth"


def test_login_failure_writes_audit_event(client, app):
    make_user(username="ivy", email="ivy@example.com")

    client.post("/api/auth/login", json={"identifier": "ivy", "password": "nope"})

    events = db.session.query(AuditLog).filter_by(action="login_failure").all()
    assert len(events) == 1
