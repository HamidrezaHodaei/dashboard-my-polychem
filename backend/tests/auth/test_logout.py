"""POST /api/auth/logout tests."""
import hashlib

from app.core.auth.models import RefreshToken
from app.extensions import db

from .factories import extract_cookie_value, login, make_user, with_refresh_cookie


def test_logout_revokes_current_refresh_token(client, app):
    make_user(username="uma", email="uma@example.com")
    token = extract_cookie_value(login(client, "uma"))

    response = client.post("/api/auth/logout", headers=with_refresh_cookie(token))

    assert response.status_code == 200
    row = (
        db.session.query(RefreshToken)
        .filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest())
        .one()
    )
    assert row.revoked_at is not None


def test_logout_clears_cookie(client, app):
    make_user(username="vince", email="vince@example.com")
    token = extract_cookie_value(login(client, "vince"))

    response = client.post("/api/auth/logout", headers=with_refresh_cookie(token))

    set_cookie_headers = response.headers.getlist("Set-Cookie")
    assert any(h.startswith("refresh_token=") for h in set_cookie_headers)


def test_logout_revoked_token_cannot_refresh_afterward(client, app):
    make_user(username="wade", email="wade@example.com")
    token = extract_cookie_value(login(client, "wade"))
    client.post("/api/auth/logout", headers=with_refresh_cookie(token))

    response = client.post("/api/auth/refresh", headers=with_refresh_cookie(token))

    assert response.status_code == 401


def test_logout_repeated_call_is_safe(client, app):
    make_user(username="vince2", email="vince2@example.com")
    token = extract_cookie_value(login(client, "vince2"))

    first = client.post("/api/auth/logout", headers=with_refresh_cookie(token))
    second = client.post("/api/auth/logout", headers=with_refresh_cookie(token))

    assert first.status_code == 200
    assert second.status_code == 200


def test_logout_without_cookie_is_safe(client, app):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
