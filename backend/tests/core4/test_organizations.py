"""HTTP tests for /api/core/organizations -- Phase 4."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import (
    auth_headers,
    grant_role_permission,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_role,
    make_user,
)


def _grant(user, key, scope_type, scope_id=None, is_delegable=False):
    permission = make_permission(key, is_delegable=is_delegable)
    grant_user_permission(user, permission, scope_type, scope_id)
    return permission


def test_create_organization_requires_permission(client, app):
    with app.app_context():
        user = make_user()
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post("/api/core/organizations", json={"name": "New Org"}, headers=headers)
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "AUTHORIZATION_ERROR"


def test_create_top_level_organization_global_grant(client, app):
    with app.app_context():
        user = make_user()
        _grant(user, "core.organization.create", ScopeType.GLOBAL)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post("/api/core/organizations", json={"name": "Top Org"}, headers=headers)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["data"]["name"] == "Top Org"
    assert body["data"]["parent_organization_id"] is None


def test_create_sub_organization_requires_only_parent_scope(client, app):
    with app.app_context():
        parent = make_organization()
        user = make_user()
        _grant(user, "core.organization.create", ScopeType.ORGANIZATION, parent.id)
        db.session.commit()
        headers = auth_headers(user)
        parent_id = parent.id

    resp = client.post(
        "/api/core/organizations",
        json={"name": "Sub Org", "parent_organization_id": parent_id},
        headers=headers,
    )
    assert resp.status_code == 201


def test_create_top_level_organization_denied_with_only_org_scoped_grant(client, app):
    """A grant scoped to ORGANIZATION:X does not cover a GLOBAL target
    (scope_covers) -- creating a *new top-level* org must still fail."""
    with app.app_context():
        other_org = make_organization()
        user = make_user()
        _grant(user, "core.organization.create", ScopeType.ORGANIZATION, other_org.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.post("/api/core/organizations", json={"name": "Top Org"}, headers=headers)
    assert resp.status_code == 403


def test_read_update_delete_single_organization(client, app):
    with app.app_context():
        org = make_organization()
        user = make_user()
        _grant(user, "core.organization.read", ScopeType.ORGANIZATION, org.id)
        _grant(user, "core.organization.update", ScopeType.ORGANIZATION, org.id)
        _grant(user, "core.organization.delete", ScopeType.ORGANIZATION, org.id)
        db.session.commit()
        headers = auth_headers(user)
        org_id = org.id

    resp = client.get(f"/api/core/organizations/{org_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.patch(
        f"/api/core/organizations/{org_id}", json={"name": "Renamed"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Renamed"

    resp = client.delete(f"/api/core/organizations/{org_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/core/organizations/{org_id}", headers=headers)
    assert resp.status_code == 404


def test_read_denied_for_a_different_organization(client, app):
    with app.app_context():
        org_a = make_organization()
        org_b = make_organization()
        user = make_user()
        _grant(user, "core.organization.read", ScopeType.ORGANIZATION, org_a.id)
        db.session.commit()
        headers = auth_headers(user)
        org_b_id = org_b.id

    resp = client.get(f"/api/core/organizations/{org_b_id}", headers=headers)
    assert resp.status_code == 403


def test_delete_blocked_when_active_departments_exist(client, app):
    with app.app_context():
        org = make_organization()
        make_department(org)
        user = make_user()
        _grant(user, "core.organization.delete", ScopeType.ORGANIZATION, org.id)
        db.session.commit()
        headers = auth_headers(user)
        org_id = org.id

    resp = client.delete(f"/api/core/organizations/{org_id}", headers=headers)
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "CONFLICT"


def test_list_filters_to_scope(client, app):
    with app.app_context():
        org_a = make_organization()
        org_b = make_organization()
        user = make_user()
        _grant(user, "core.organization.read", ScopeType.ORGANIZATION, org_a.id)
        db.session.commit()
        headers = auth_headers(user)
        org_a_id, org_b_id = org_a.id, org_b.id

    resp = client.get("/api/core/organizations", headers=headers)
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.get_json()["data"]}
    assert org_a_id in ids
    assert org_b_id not in ids


def test_list_sees_everything_with_global_grant(client, app):
    with app.app_context():
        make_organization()
        make_organization()
        user = make_user()
        _grant(user, "core.organization.read", ScopeType.GLOBAL)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/core/organizations", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] >= 2


def test_role_scoped_grant_also_works_not_just_direct_user_grant(client, app):
    with app.app_context():
        org = make_organization()
        role = make_role()
        permission = make_permission("core.organization.read")
        grant_role_permission(role, permission, ScopeType.ORGANIZATION, org.id)
        user = make_user()
        from tests.core4.factories import assign_role
        assign_role(user, role)
        db.session.commit()
        headers = auth_headers(user)
        org_id = org.id

    resp = client.get(f"/api/core/organizations/{org_id}", headers=headers)
    assert resp.status_code == 200
