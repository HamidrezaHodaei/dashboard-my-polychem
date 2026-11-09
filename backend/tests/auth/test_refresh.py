"""POST /api/auth/refresh tests -- rotation, reuse detection, chain-wide revocation."""
import hashlib
from datetime import datetime, timedelta, timezone

from app.core.audit_logs.models import AuditLog
from app.core.auth.models import RefreshToken
from app.extensions import db

from .factories import extract_cookie_value, login, make_user, with_refresh_cookie


def test_refresh_valid_returns_new_access_token_and_rotated_cookie(client, app):
    make_user(username="oscar", email="oscar@example.com")
    login_response = login(client, "oscar")
    old_token = extract_cookie_value(login_response)

    response = client.post("/api/auth/refresh", headers=with_refresh_cookie(old_token))

    assert response.status_code == 200
    assert "access_token" in response.get_json()["data"]
    new_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(h.startswith("refresh_token=") for h in new_cookie_headers)
    new_token = extract_cookie_value(response)
    assert new_token is not None
    assert new_token != old_token


def test_refresh_old_token_rejected_after_rotation(client, app):
    make_user(username="paul", email="paul@example.com")
    old_token = extract_cookie_value(login(client, "paul"))

    first = client.post("/api/auth/refresh", headers=with_refresh_cookie(old_token))
    assert first.status_code == 200

    second = client.post("/api/auth/refresh", headers=with_refresh_cookie(old_token))
    assert second.status_code == 401
    assert second.get_json()["error"]["message"] == "Invalid refresh token."


def test_refresh_reuse_triggers_chain_wide_revocation(client, app):
    user = make_user(username="quinn", email="quinn@example.com")
    original_token = extract_cookie_value(login(client, "quinn"))

    first_rotation = client.post("/api/auth/refresh", headers=with_refresh_cookie(original_token))
    rotated_token = extract_cookie_value(first_rotation)
    assert rotated_token is not None

    # Reusing the ORIGINAL (already-rotated) token is the theft signal.
    reused = client.post("/api/auth/refresh", headers=with_refresh_cookie(original_token))
    assert reused.status_code == 401

    # The token issued FROM that rotation must also now be revoked, even
    # though it was never itself reused -- chain-wide revocation.
    after_reuse = client.post("/api/auth/refresh", headers=with_refresh_cookie(rotated_token))
    assert after_reuse.status_code == 401

    rows = db.session.query(RefreshToken).filter_by(user_id=user.id).all()
    assert len(rows) >= 2
    assert all(row.revoked_at is not None for row in rows)


def test_refresh_reuse_writes_audit_events(client, app):
    make_user(username="quinn2", email="quinn2@example.com")
    original_token = extract_cookie_value(login(client, "quinn2"))
    client.post("/api/auth/refresh", headers=with_refresh_cookie(original_token))

    client.post("/api/auth/refresh", headers=with_refresh_cookie(original_token))

    assert db.session.query(AuditLog).filter_by(action="refresh_reuse_detected").count() == 1
    assert db.session.query(AuditLog).filter_by(action="refresh_revoked").count() == 1


def test_refresh_no_new_access_token_issued_on_reuse(client, app):
    make_user(username="ray", email="ray@example.com")
    original_token = extract_cookie_value(login(client, "ray"))
    client.post("/api/auth/refresh", headers=with_refresh_cookie(original_token))

    reused = client.post("/api/auth/refresh", headers=with_refresh_cookie(original_token))

    assert reused.status_code == 401
    assert "access_token" not in (reused.get_json().get("data") or {})


def test_refresh_expired_token_rejected(client, app):
    user = make_user(username="ruth", email="ruth@example.com")
    raw_token = "an-expired-raw-refresh-token"
    row = RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        issued_at=datetime.now(timezone.utc) - timedelta(days=20),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.session.add(row)
    db.session.commit()

    response = client.post("/api/auth/refresh", headers=with_refresh_cookie(raw_token))

    assert response.status_code == 401


def test_refresh_revoked_token_rejected(client, app):
    user = make_user(username="steve", email="steve@example.com")
    raw_token = "a-revoked-raw-refresh-token"
    row = RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
        revoked_at=datetime.now(timezone.utc),
    )
    db.session.add(row)
    db.session.commit()

    response = client.post("/api/auth/refresh", headers=with_refresh_cookie(raw_token))

    assert response.status_code == 401


def test_refresh_missing_cookie_rejected(client, app):
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401


def test_refresh_unknown_token_rejected(client, app):
    response = client.post(
        "/api/auth/refresh", headers=with_refresh_cookie("this-token-was-never-issued")
    )
    assert response.status_code == 401


def test_refresh_inactive_user_cannot_refresh(client, app):
    user = make_user(username="sam", email="sam@example.com")
    token = extract_cookie_value(login(client, "sam"))
    user.is_active = False
    db.session.commit()

    response = client.post("/api/auth/refresh", headers=with_refresh_cookie(token))

    assert response.status_code == 401


def test_refresh_soft_deleted_user_cannot_refresh(client, app):
    user = make_user(username="tara", email="tara@example.com")
    token = extract_cookie_value(login(client, "tara"))
    user.deleted_at = datetime.now(timezone.utc)
    db.session.commit()

    response = client.post("/api/auth/refresh", headers=with_refresh_cookie(token))

    assert response.status_code == 401


def test_refresh_replacement_relationship_stored_correctly(client, app):
    user = make_user(username="tina", email="tina@example.com")
    old_token = extract_cookie_value(login(client, "tina"))
    old_row = db.session.query(RefreshToken).filter_by(user_id=user.id).one()

    client.post("/api/auth/refresh", headers=with_refresh_cookie(old_token))

    db.session.refresh(old_row)
    assert old_row.revoked_at is not None
    assert old_row.replaced_by_token_id is not None

    new_row = db.session.get(RefreshToken, old_row.replaced_by_token_id)
    assert new_row is not None
    assert new_row.revoked_at is None
    assert new_row.user_id == user.id
