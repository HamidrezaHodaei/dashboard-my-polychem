"""Reload / second-tab race: a just-rotated refresh token may be replayed briefly without logout."""
from datetime import datetime, timedelta, timezone

from app.core.auth.models import RefreshToken
from app.extensions import db

from .factories import extract_cookie_value, login, make_user, with_refresh_cookie


def test_replay_within_grace_window_keeps_the_session_alive(client, app):
    app.config["REFRESH_REUSE_GRACE_SECONDS"] = 30
    make_user(username="grace1", email="grace1@example.com")
    old = extract_cookie_value(login(client, "grace1"))

    first = client.post("/api/auth/refresh", headers=with_refresh_cookie(old))
    newer = extract_cookie_value(first)
    replay = client.post("/api/auth/refresh", headers=with_refresh_cookie(old))

    assert replay.status_code == 200 and "access_token" in replay.get_json()["data"]
    assert extract_cookie_value(replay) is None  # never overwrites the newer cookie
    # ...and the newer token is still valid: no chain-wide revocation happened.
    assert client.post("/api/auth/refresh", headers=with_refresh_cookie(newer)).status_code == 200


def test_replay_after_grace_window_is_still_theft(client, app):
    app.config["REFRESH_REUSE_GRACE_SECONDS"] = 30
    make_user(username="grace2", email="grace2@example.com")
    old = extract_cookie_value(login(client, "grace2"))
    newer = extract_cookie_value(client.post("/api/auth/refresh", headers=with_refresh_cookie(old)))

    for row in db.session.query(RefreshToken).filter(RefreshToken.revoked_at.isnot(None)).all():
        row.revoked_at = datetime.now(timezone.utc) - timedelta(seconds=600)
    db.session.commit()

    assert client.post("/api/auth/refresh", headers=with_refresh_cookie(old)).status_code == 401
    assert client.post("/api/auth/refresh", headers=with_refresh_cookie(newer)).status_code == 401


def test_logged_out_token_gets_no_grace(client, app):
    app.config["REFRESH_REUSE_GRACE_SECONDS"] = 30
    make_user(username="grace3", email="grace3@example.com")
    token = extract_cookie_value(login(client, "grace3"))
    client.post("/api/auth/logout", headers=with_refresh_cookie(token))
    assert client.post("/api/auth/refresh", headers=with_refresh_cookie(token)).status_code == 401


def test_access_token_default_lifetime_is_12_hours(app):
    assert app.config["JWT_ACCESS_TOKEN_EXPIRES"] == timedelta(hours=12)
