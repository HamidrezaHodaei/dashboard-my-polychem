"""HTTP tests for /api/core/departments -- Phase 4."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import (
    auth_headers,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_team,
    make_user,
)


def _grant(user, key, scope_type, scope_id=None):
    permission = make_permission(key)
    grant_user_permission(user, permission, scope_type, scope_id)
    return permission


def test_create_department_requires_organization_scope(client, app):
    with app.app_context():
        org = make_organization()
        user = make_user()
        _grant(user, "core.department.create", ScopeType.ORGANIZATION, org.id)
        db.session.commit()
        headers = auth_headers(user)
        org_id = org.id

    resp = client.post(
        "/api/core/departments",
        json={"name": "New Dept", "organization_id": org_id},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["organization_id"] == org_id


def test_create_department_denied_for_other_organization(client, app):
    with app.app_context():
        org_a = make_organization()
        org_b = make_organization()
        user = make_user()
        _grant(user, "core.department.create", ScopeType.ORGANIZATION, org_a.id)
        db.session.commit()
        headers = auth_headers(user)
        org_b_id = org_b.id

    resp = client.post(
        "/api/core/departments",
        json={"name": "Dept", "organization_id": org_b_id},
        headers=headers,
    )
    assert resp.status_code == 403


def test_update_delete_department(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "core.department.update", ScopeType.DEPARTMENT, dept.id)
        _grant(user, "core.department.delete", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    resp = client.patch(
        f"/api/core/departments/{dept_id}", json={"name": "Renamed Dept"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Renamed Dept"

    resp = client.delete(f"/api/core/departments/{dept_id}", headers=headers)
    assert resp.status_code == 200


def test_delete_blocked_when_active_teams_exist(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        make_team(dept)
        user = make_user()
        _grant(user, "core.department.delete", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    resp = client.delete(f"/api/core/departments/{dept_id}", headers=headers)
    assert resp.status_code == 409


def test_list_filters_by_organization_scope(client, app):
    with app.app_context():
        org_a = make_organization()
        org_b = make_organization()
        dept_a = make_department(org_a)
        dept_b = make_department(org_b)
        user = make_user()
        _grant(user, "core.department.read", ScopeType.ORGANIZATION, org_a.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_a_id, dept_b_id = dept_a.id, dept_b.id

    resp = client.get("/api/core/departments", headers=headers)
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.get_json()["data"]}
    assert dept_a_id in ids
    assert dept_b_id not in ids
