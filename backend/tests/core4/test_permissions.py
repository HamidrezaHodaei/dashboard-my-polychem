"""HTTP tests for /api/core/permissions -- Phase 4."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import (
    auth_headers,
    grant_role_permission,
    grant_user_permission,
    make_permission,
    make_role,
    make_user,
)


def _grant(user, key):
    permission = make_permission(key)
    grant_user_permission(user, permission, ScopeType.GLOBAL, None)
    return permission


def test_create_permission(client, app):
    with app.app_context():
        user = make_user()
        _grant(user, "core.permission.create")
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post(
        "/api/core/permissions", json={"key": "crm.customer.read"}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["module"] == "crm"
    assert body["resource"] == "customer"
    assert body["action"] == "read"


def test_create_permission_rejects_malformed_key(client, app):
    with app.app_context():
        user = make_user()
        _grant(user, "core.permission.create")
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post("/api/core/permissions", json={"key": "not-a-valid-key"}, headers=headers)
    assert resp.status_code == 400


def test_permission_in_use_cannot_be_deleted(client, app):
    with app.app_context():
        role = make_role()
        permission = make_permission("crm.customer.read")
        grant_role_permission(role, permission, ScopeType.GLOBAL, None)
        user = make_user()
        _grant(user, "core.permission.delete")
        db.session.commit()
        headers = auth_headers(user)
        permission_id = permission.id

    resp = client.delete(f"/api/core/permissions/{permission_id}", headers=headers)
    assert resp.status_code == 409


def test_unused_permission_can_be_deleted(client, app):
    with app.app_context():
        permission = make_permission("crm.customer.read")
        user = make_user()
        _grant(user, "core.permission.delete")
        db.session.commit()
        headers = auth_headers(user)
        permission_id = permission.id

    resp = client.delete(f"/api/core/permissions/{permission_id}", headers=headers)
    assert resp.status_code == 200
