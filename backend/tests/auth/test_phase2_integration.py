"""
Proves the intended Phase 3 -> Phase 2 integration flow end to end,
without modifying a single line of app/permissions/*:

    Authorization header -> JWT validation -> User lookup
        -> g.current_user -> require_permission(...) -> Phase 2 engine

Registers a throwaway route on the (function-scoped, fresh-per-test)
`app` fixture rather than adding a real endpoint to the app -- this is
purely a Phase 2/Phase 3 wiring proof, not a new product feature.
"""
from flask import g, jsonify

from app.core.auth.decorators import require_authenticated
from app.core.authorization.models import ScopeType
from app.permissions.decorators import require_permission

from tests.permissions.factories import grant_user_permission, make_permission

from .factories import login, make_user


def test_authenticated_user_with_permission_reaches_the_view(client, app):
    user = make_user(username="mia", email="mia@example.com")
    permission = make_permission("tasks.task.read")
    grant_user_permission(user, permission, ScopeType.GLOBAL)

    @app.route("/api/_test/protected")
    @require_authenticated
    @require_permission("tasks.task.read")
    def protected_view():
        return jsonify({"current_user_id": g.current_user.id})

    token = login(client, "mia").get_json()["data"]["access_token"]
    response = client.get("/api/_test/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json()["current_user_id"] == user.id


def test_authenticated_user_without_permission_gets_403(client, app):
    make_user(username="nina", email="nina@example.com")
    make_permission("tasks.task.read")  # exists, but never granted to nina

    @app.route("/api/_test/protected2")
    @require_authenticated
    @require_permission("tasks.task.read")
    def protected_view_2():
        return jsonify({"ok": True})

    token = login(client, "nina").get_json()["data"]["access_token"]
    response = client.get("/api/_test/protected2", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "AUTHORIZATION_ERROR"


def test_unauthenticated_request_never_reaches_permission_check(client, app):
    make_permission("tasks.task.read")

    @app.route("/api/_test/protected3")
    @require_authenticated
    @require_permission("tasks.task.read")
    def protected_view_3():  # pragma: no cover - should never execute
        return jsonify({"ok": True})

    response = client.get("/api/_test/protected3")  # no Authorization header

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "AUTHENTICATION_ERROR"
