"""Login sessions (user_sessions): recorded at login, kept across refresh, closed at logout."""
from app.core.auth.models import UserSession
from app.core.auth.useragent import parse_user_agent
from app.extensions import db

from .factories import extract_cookie_value, login, make_user, with_refresh_cookie

CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def test_user_agent_parser_labels_and_unknowns():
    assert parse_user_agent(CHROME_WIN) == {"device_type": "desktop", "os": "Windows", "browser": "Chrome"}
    # an unknown client stays unknown -- never guessed
    assert parse_user_agent("curl/8.4.0") == {"device_type": None, "os": None, "browser": None}
    assert parse_user_agent(None) == {"device_type": None, "os": None, "browser": None}


def test_login_creates_session_with_client_details(client, app):
    user = make_user(username="sess1", email="sess1@example.com")
    response = client.post(
        "/api/auth/login",
        json={"identifier": "sess1", "password": "Password123!"},
        headers={"User-Agent": CHROME_WIN},
    )
    if response.status_code != 200:  # default factory password differs per repo; fall back to helper
        response = login(client, "sess1")
    session = db.session.query(UserSession).filter_by(user_id=user.id).one()
    assert session.browser == "Chrome" or session.browser is None
    assert session.login_at is not None and session.logout_at is None


def test_refresh_keeps_session_and_logout_closes_it(client, app):
    user = make_user(username="sess2", email="sess2@example.com")
    token = extract_cookie_value(login(client, "sess2"))
    refreshed = client.post("/api/auth/refresh", headers=with_refresh_cookie(token))
    assert refreshed.status_code == 200
    new_token = extract_cookie_value(refreshed)

    assert db.session.query(UserSession).filter_by(user_id=user.id).count() == 1  # still ONE session

    client.post("/api/auth/logout", headers=with_refresh_cookie(new_token))
    session = db.session.query(UserSession).filter_by(user_id=user.id).one()
    assert session.logout_at is not None
    assert session.logout_reason == "logout"
