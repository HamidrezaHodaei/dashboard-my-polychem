"""GET /api/me/permissions -- AUTHORIZATION.md §5's Effective Grants,
reshaped for the API. Uses tests/core4/factories.py's RBAC builders and
auth_headers() (mints a JWT directly) since these tests care about
permission/scope resolution outcomes, not login itself."""
from app.core.authorization.models import ScopeType
from app.extensions import db
from tests.core4.factories import (
    auth_headers,
    assign_role,
    grant_role_permission,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_role,
    make_team,
    make_user,
)


def test_me_permissions_unauthenticated_returns_401(client):
    resp = client.get("/api/me/permissions")
    assert resp.status_code == 401


def test_me_permissions_user_with_no_permissions_returns_empty_list(app, client):
    with app.app_context():
        user = make_user()
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/permissions", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["permissions"] == []


def test_me_permissions_role_grant_appears_with_scope_and_source(app, client):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        role = make_role()
        assign_role(user, role)
        permission = make_permission("tasks.task.read")
        grant_role_permission(role, permission, ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    resp = client.get("/api/me/permissions", headers=headers)
    body = resp.get_json()["data"]["permissions"]
    assert len(body) == 1
    assert body[0]["key"] == "tasks.task.read"
    assert body[0]["scopes"] == [
        {"scope_type": "DEPARTMENT", "scope_id": dept_id, "source": "role"}
    ]


def test_me_permissions_direct_user_grant_appears_with_source_user(app, client):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        permission = make_permission("tasks.task.create")
        grant_user_permission(user, permission, ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/permissions", headers=headers)
    body = resp.get_json()["data"]["permissions"]
    assert body[0]["scopes"][0]["source"] == "user"


def test_me_permissions_multiple_roles_are_unioned(app, client):
    with app.app_context():
        org = make_organization()
        dept_a = make_department(org)
        dept_b = make_department(org)
        user = make_user()
        role_a = make_role()
        role_b = make_role()
        assign_role(user, role_a)
        assign_role(user, role_b)
        perm_a = make_permission("tasks.task.read")
        perm_b = make_permission("tasks.task.create")
        grant_role_permission(role_a, perm_a, ScopeType.DEPARTMENT, dept_a.id)
        grant_role_permission(role_b, perm_b, ScopeType.DEPARTMENT, dept_b.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/permissions", headers=headers)
    keys = {item["key"] for item in resp.get_json()["data"]["permissions"]}
    assert keys == {"tasks.task.read", "tasks.task.create"}


def test_me_permissions_same_key_from_role_and_user_grant_both_listed(app, client):
    """Effective permissions are a UNION of both grant sources -- when a
    role grant and a direct user grant both exist for the same
    permission key (at different scopes), both scopes must appear under
    the one grouped entry, not just one of them."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        user = make_user()
        role = make_role()
        assign_role(user, role)
        permission = make_permission("tasks.task.assign")
        grant_role_permission(role, permission, ScopeType.DEPARTMENT, dept.id)
        grant_user_permission(user, permission, ScopeType.TEAM, team.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/permissions", headers=headers)
    body = resp.get_json()["data"]["permissions"]
    assert len(body) == 1
    assert body[0]["key"] == "tasks.task.assign"
    sources = {s["source"] for s in body[0]["scopes"]}
    assert sources == {"role", "user"}


def test_me_permissions_reflects_organization_scope(app, client):
    with app.app_context():
        org = make_organization()
        user = make_user()
        permission = make_permission("core.department.read")
        grant_user_permission(user, permission, ScopeType.ORGANIZATION, org.id)
        db.session.commit()
        headers = auth_headers(user)
        org_id = org.id

    resp = client.get("/api/me/permissions", headers=headers)
    body = resp.get_json()["data"]["permissions"]
    assert body[0]["scopes"][0] == {
        "scope_type": "ORGANIZATION", "scope_id": org_id, "source": "user",
    }


def test_me_permissions_inactive_role_grant_excluded(app, client):
    """AUTHORIZATION.md §5: only ACTIVE role grants count -- an inactive
    role must not contribute its permissions to the effective set."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        role = make_role(is_active=False)
        assign_role(user, role)
        permission = make_permission("tasks.task.read")
        grant_role_permission(role, permission, ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/permissions", headers=headers)
    assert resp.get_json()["data"]["permissions"] == []


def test_me_permissions_delegated_grant_appears_as_user_source(app, client):
    """DATABASE.md: a delegation's *result* is an ordinary
    user_permission_scopes row -- this simulates that shape directly
    (granted_by_user_id set to the delegator) rather than re-running the
    delegation service, since /api/me/permissions only needs to prove it
    reads the same effective-grants resolution that already includes
    every user_permission_scopes row, delegated or not."""
    with app.app_context():
        org = make_organization()
        team = make_team(make_department(org))
        delegator = make_user()
        delegatee = make_user()
        permission = make_permission("tasks.task.assign", is_delegable=True)
        grant_user_permission(
            delegatee, permission, ScopeType.TEAM, team.id, granted_by=delegator
        )
        db.session.commit()
        headers = auth_headers(delegatee)

    resp = client.get("/api/me/permissions", headers=headers)
    body = resp.get_json()["data"]["permissions"]
    assert body[0]["key"] == "tasks.task.assign"
    assert body[0]["scopes"][0]["source"] == "user"


def test_me_permissions_never_leaks_sensitive_fields(app, client):
    with app.app_context():
        user = make_user()
        permission = make_permission("tasks.task.read")
        grant_user_permission(user, permission, ScopeType.GLOBAL, None)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/permissions", headers=headers)
    body_text = resp.get_data(as_text=True)
    assert "password_hash" not in body_text
    assert "token_hash" not in body_text
