"""HTTP tests for /api/core/users -- Phase 4."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import (
    auth_headers,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_role,
    make_user,
)


def _grant(user, key, scope_type, scope_id=None):
    permission = make_permission(key)
    grant_user_permission(user, permission, scope_type, scope_id)
    return permission


def test_create_user_in_department(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        manager = make_user()
        _grant(manager, "core.user.create", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(manager)
        dept_id = dept.id

    resp = client.post(
        "/api/core/users",
        json={
            "full_name": "New Hire",
            "email": "new.hire@example.com",
            "username": "newhire",
            "password": "Str0ng-P@ssw0rd!",
            "department_id": dept_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["department_id"] == dept_id
    assert "password" not in body
    assert "password_hash" not in body


def test_department_manager_can_list_and_edit_users_within_department_not_globally(client, app):
    """IMPLEMENTATION_PLAN.md Phase 4's own example: 'a department
    manager can list/edit users within their own department, not
    globally.'"""
    with app.app_context():
        org = make_organization()
        dept_a = make_department(org)
        dept_b = make_department(org)
        in_scope = make_user(department_id=dept_a.id)
        out_of_scope = make_user(department_id=dept_b.id)
        manager = make_user()
        _grant(manager, "core.user.read", ScopeType.DEPARTMENT, dept_a.id)
        _grant(manager, "core.user.update", ScopeType.DEPARTMENT, dept_a.id)
        db.session.commit()
        headers = auth_headers(manager)
        in_scope_id, out_of_scope_id = in_scope.id, out_of_scope.id

    # list only shows dept_a's user
    resp = client.get("/api/core/users", headers=headers)
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.get_json()["data"]}
    assert in_scope_id in ids
    assert out_of_scope_id not in ids

    # can edit the in-scope user
    resp = client.patch(
        f"/api/core/users/{in_scope_id}", json={"full_name": "Renamed"}, headers=headers
    )
    assert resp.status_code == 200

    # cannot read or edit the out-of-scope user
    resp = client.get(f"/api/core/users/{out_of_scope_id}", headers=headers)
    assert resp.status_code == 403
    resp = client.patch(
        f"/api/core/users/{out_of_scope_id}", json={"full_name": "Nope"}, headers=headers
    )
    assert resp.status_code == 403


def test_user_cannot_delete_own_account(client, app):
    with app.app_context():
        user = make_user()
        _grant(user, "core.user.delete", ScopeType.GLOBAL)
        db.session.commit()
        headers = auth_headers(user)
        user_id = user.id

    resp = client.delete(f"/api/core/users/{user_id}", headers=headers)
    assert resp.status_code == 409


def test_duplicate_email_conflict(client, app):
    with app.app_context():
        make_user(email="taken@example.com")
        manager = make_user()
        _grant(manager, "core.user.create", ScopeType.GLOBAL)
        db.session.commit()
        headers = auth_headers(manager)

    resp = client.post(
        "/api/core/users",
        json={
            "full_name": "Someone",
            "email": "taken@example.com",
            "username": "someoneelse",
            "password": "Str0ng-P@ssw0rd!",
        },
        headers=headers,
    )
    assert resp.status_code == 409


def test_assign_and_revoke_role(client, app):
    with app.app_context():
        target = make_user()
        role = make_role()
        manager = make_user()
        _grant(manager, "core.user.update", ScopeType.GLOBAL)
        db.session.commit()
        headers = auth_headers(manager)
        target_id, role_id = target.id, role.id

    resp = client.post(
        f"/api/core/users/{target_id}/roles", json={"role_id": role_id}, headers=headers
    )
    assert resp.status_code == 201

    resp = client.delete(f"/api/core/users/{target_id}/roles/{role_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.delete(f"/api/core/users/{target_id}/roles/{role_id}", headers=headers)
    assert resp.status_code == 404


def test_list_user_roles(client, app):
    with app.app_context():
        target = make_user()
        role = make_role()
        manager = make_user()
        _grant(manager, "core.user.update", ScopeType.GLOBAL)
        _grant(manager, "core.user.read", ScopeType.GLOBAL)
        db.session.commit()
        headers = auth_headers(manager)
        target_id, role_id = target.id, role.id

    client.post(f"/api/core/users/{target_id}/roles", json={"role_id": role_id}, headers=headers)

    resp = client.get(f"/api/core/users/{target_id}/roles", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body) == 1
    assert body[0]["role_id"] == role_id
    assert body[0]["user_id"] == target_id


def test_list_user_roles_denied_without_read_permission(client, app):
    with app.app_context():
        target = make_user()
        outsider = make_user()
        db.session.commit()
        headers = auth_headers(outsider)
        target_id = target.id

    resp = client.get(f"/api/core/users/{target_id}/roles", headers=headers)
    assert resp.status_code == 403
