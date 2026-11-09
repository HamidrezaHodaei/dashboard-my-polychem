"""
Access-token validation tests -- app/core/auth/decorators.py's
`require_authenticated`, exercised via GET /api/me (the only protected
route Phase 3 ships).
"""
from datetime import timedelta

from flask_jwt_extended import create_access_token

from app.extensions import db

from .factories import login, make_user


def test_me_missing_token_denied(client, app):
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_me_valid_token_populates_current_user(client, app):
    make_user(username="iris", email="iris@example.com")
    token = login(client, "iris").get_json()["data"]["access_token"]

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json()["data"]["username"] == "iris"


def test_me_malformed_token_denied(client, app):
    response = client.get("/api/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_me_expired_token_denied(client, app):
    user = make_user(username="jack", email="jack@example.com")
    expired_token = create_access_token(identity=str(user.id), expires_delta=timedelta(seconds=-1))

    response = client.get("/api/me", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401


def test_me_invalid_subject_denied(client, app):
    token = create_access_token(identity="not-a-valid-user-id")

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_nonexistent_user_id_denied(client, app):
    token = create_access_token(identity="999999")

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_inactive_user_denied(client, app):
    user = make_user(username="karen", email="karen@example.com")
    token = create_access_token(identity=str(user.id))
    user.is_active = False
    db.session.commit()

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_soft_deleted_user_denied(client, app):
    from datetime import datetime, timezone

    user = make_user(username="leo", email="leo@example.com")
    token = create_access_token(identity=str(user.id))
    user.deleted_at = datetime.now(timezone.utc)
    db.session.commit()

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
