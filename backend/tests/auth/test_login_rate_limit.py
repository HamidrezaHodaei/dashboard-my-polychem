"""
POST /api/auth/login rate-limit test.

Kept separate from tests/conftest.py's `app`/`client` fixtures, which
run with RATELIMIT_ENABLED=False (TestingConfig) precisely to keep the
rest of the suite deterministic and not rate-limit-sensitive. This one
test builds its own app instance with rate limiting turned back on and
a low, deterministic threshold, so it doesn't affect (or get affected
by) any other test.
"""
from app import create_app
from app.extensions import db as _db

from .factories import make_user


def test_login_rate_limit_triggers_after_threshold():
    application = create_app("testing")
    application.config["RATELIMIT_ENABLED"] = True
    application.config["LOGIN_RATE_LIMIT"] = "2 per minute"

    with application.app_context():
        _db.create_all()
        try:
            test_client = application.test_client()
            make_user(username="henry", email="henry@example.com")

            first = test_client.post(
                "/api/auth/login", json={"identifier": "henry", "password": "wrong"}
            )
            second = test_client.post(
                "/api/auth/login", json={"identifier": "henry", "password": "wrong"}
            )
            third = test_client.post(
                "/api/auth/login", json={"identifier": "henry", "password": "wrong"}
            )

            assert first.status_code == 401
            assert second.status_code == 401
            assert third.status_code == 429
            assert third.get_json()["error"]["code"] == "RATE_LIMITED"
        finally:
            _db.session.remove()
            _db.drop_all()
