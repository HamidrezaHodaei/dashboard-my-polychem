"""
Shared test-data builders and HTTP helpers for Phase 3 auth tests.

Kept separate from tests/permissions/factories.py deliberately: that
module's `make_user` uses a placeholder, never-verified password_hash
(fine for Phase 2, which never logs anyone in); Phase 3 tests need a
REAL Argon2 hash so login can actually succeed/fail meaningfully.
"""
import itertools

from app.core.auth import services
from app.core.users.models import User
from app.extensions import db

_counter = itertools.count()

DEFAULT_PASSWORD = "Str0ng-P@ssw0rd!"


def make_user(password: str = DEFAULT_PASSWORD, **overrides) -> User:
    n = next(_counter)
    defaults = dict(
        full_name=f"User {n}",
        email=f"user{n}@example.com",
        username=f"user{n}",
        password_hash=services.hash_password(password),
    )
    defaults.update(overrides)
    user = User(**defaults)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, identifier: str, password: str = DEFAULT_PASSWORD):
    return client.post("/api/auth/login", json={"identifier": identifier, "password": password})


def extract_cookie_value(response, name: str = "refresh_token") -> str | None:
    """Pull the raw cookie value out of a response's Set-Cookie headers,
    without relying on the test client's automatic cookie jar (which
    always presents the LATEST value -- several tests need to
    deliberately re-present an older one)."""
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(f"{name}="):
            return header.split(";", 1)[0].split("=", 1)[1]
    return None


def with_refresh_cookie(raw_token: str) -> dict:
    """Headers dict presenting an explicit refresh_token cookie value,
    bypassing the test client's jar."""
    return {"Cookie": f"refresh_token={raw_token}"} if raw_token else {}
