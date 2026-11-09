"""HTTP tests for /api/core/roles -- Phase 4."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import assign_role, auth_headers, grant_user_permission, make_permission, make_role, make_user


def _grant(user, key, scope_type=ScopeType.GLOBAL, scope_id=None):
    permission = make_permission(key)
    grant_user_permission(user, permission, scope_type, scope_id)
    return permission


def test_create_role_requires_global_grant(client, app):
    with app.app_context():
        user = make_user()
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post(
        "/api/core/roles", json={"name": "custom_role", "display_name": "Custom"}, headers=headers
    )
    assert resp.status_code == 403


def test_create_and_update_role(client, app):
    with app.app_context():
        user = make_user()
        _grant(user, "core.role.create")
        _grant(user, "core.role.update")
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post(
        "/api/core/roles", json={"name": "custom_role", "display_name": "Custom"}, headers=headers
    )
    assert resp.status_code == 201
    role_id = resp.get_json()["data"]["id"]
    assert resp.get_json()["data"]["is_system_role"] is False

    resp = client.patch(
        f"/api/core/roles/{role_id}", json={"display_name": "Renamed Role"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["display_name"] == "Renamed Role"


def test_system_role_cannot_be_deleted(client, app):
    with app.app_context():
        role = make_role(is_system_role=True)
        user = make_user()
        _grant(user, "core.role.delete")
        db.session.commit()
        headers = auth_headers(user)
        role_id = role.id

    resp = client.delete(f"/api/core/roles/{role_id}", headers=headers)
    assert resp.status_code == 409


def test_role_still_held_by_a_user_cannot_be_deleted(client, app):
    with app.app_context():
        role = make_role()
        holder = make_user()
        assign_role(holder, role)
        user = make_user()
        _grant(user, "core.role.delete")
        db.session.commit()
        headers = auth_headers(user)
        role_id = role.id

    resp = client.delete(f"/api/core/roles/{role_id}", headers=headers)
    assert resp.status_code == 409


def test_ordinary_role_with_no_holders_can_be_deleted(client, app):
    with app.app_context():
        role = make_role()
        user = make_user()
        _grant(user, "core.role.delete")
        db.session.commit()
        headers = auth_headers(user)
        role_id = role.id

    resp = client.delete(f"/api/core/roles/{role_id}", headers=headers)
    assert resp.status_code == 200


def test_department_scoped_grant_does_not_cover_roles(client, app):
    """Roles are GLOBAL-only entities -- a DEPARTMENT-scoped grant must
    never satisfy a core.role.* check (scope_covers rank ordering)."""
    with app.app_context():
        from tests.core4.factories import make_department, make_organization

        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "core.role.read", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/core/roles", headers=headers)
    assert resp.status_code == 403


def test_grant_and_revoke_role_permission(client, app):
    with app.app_context():
        role = make_role()
        permission = make_permission("core.department.read")
        manager = make_user()
        _grant(manager, "core.role.update")
        _grant(manager, "core.role.read")
        db.session.commit()
        headers = auth_headers(manager)
        role_id, permission_id = role.id, permission.id

    resp = client.post(
        f"/api/core/roles/{role_id}/permissions",
        json={"permission_id": permission_id, "scope_type": "GLOBAL"},
        headers=headers,
    )
    assert resp.status_code == 201
    grant_id = resp.get_json()["data"]["id"]
    assert resp.get_json()["data"]["scope_type"] == "GLOBAL"

    resp = client.get(f"/api/core/roles/{role_id}/permissions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 1

    resp = client.delete(f"/api/core/roles/{role_id}/permissions/{grant_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/core/roles/{role_id}/permissions", headers=headers)
    assert resp.get_json()["data"] == []


def test_grant_role_permission_requires_valid_scope_target(client, app):
    with app.app_context():
        role = make_role()
        permission = make_permission("core.department.read")
        manager = make_user()
        _grant(manager, "core.role.update")
        db.session.commit()
        headers = auth_headers(manager)
        role_id, permission_id = role.id, permission.id

    resp = client.post(
        f"/api/core/roles/{role_id}/permissions",
        json={"permission_id": permission_id, "scope_type": "DEPARTMENT", "scope_id": 999999},
        headers=headers,
    )
    assert resp.status_code == 404


def test_grant_role_permission_denied_without_update_permission(client, app):
    with app.app_context():
        role = make_role()
        permission = make_permission("core.department.read")
        user = make_user()
        db.session.commit()
        headers = auth_headers(user)
        role_id, permission_id = role.id, permission.id

    resp = client.post(
        f"/api/core/roles/{role_id}/permissions",
        json={"permission_id": permission_id, "scope_type": "GLOBAL"},
        headers=headers,
    )
    assert resp.status_code == 403
