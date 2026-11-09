"""GET /api/me/navigation -- permission-filtered menu tree (API.md)."""
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


def test_me_navigation_unauthenticated_returns_401(client):
    resp = client.get("/api/me/navigation")
    assert resp.status_code == 401


def test_me_navigation_user_with_no_permissions_returns_empty_list(app, client):
    with app.app_context():
        user = make_user()
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/navigation", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["navigation"] == []


def test_me_navigation_shows_only_permitted_entries(app, client):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        permission = make_permission("tasks.task.read")
        grant_user_permission(user, permission, ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/navigation", headers=headers)
    body = resp.get_json()["data"]["navigation"]
    assert len(body) == 1
    assert body[0] == {
        "key": "tasks", "label": "Tasks", "path": "/tasks", "permission": "tasks.task.read",
    }


def test_me_navigation_visible_regardless_of_which_scope_grant_is_at(app, client):
    """Navigation visibility is step-1-only (holds the permission at ALL
    -- any scope), unlike an actual resource action."""
    with app.app_context():
        team = make_team(make_department(make_organization()))
        user = make_user()
        permission = make_permission("tasks.analytics.read")
        grant_user_permission(user, permission, ScopeType.TEAM, team.id)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/navigation", headers=headers)
    keys = {item["key"] for item in resp.get_json()["data"]["navigation"]}
    assert keys == {"task_analytics"}


def test_me_navigation_multiple_roles_union_and_catalog_order(app, client):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        role_tasks = make_role()
        role_users = make_role()
        assign_role(user, role_tasks)
        assign_role(user, role_users)
        grant_role_permission(
            role_tasks, make_permission("tasks.task.read"), ScopeType.DEPARTMENT, dept.id
        )
        grant_role_permission(
            role_users, make_permission("core.user.read"), ScopeType.DEPARTMENT, dept.id
        )
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/navigation", headers=headers)
    body = resp.get_json()["data"]["navigation"]
    # Catalog order is users, then tasks -- must be preserved regardless
    # of which role/grant was created first.
    assert [item["key"] for item in body] == ["users", "tasks"]


def test_me_navigation_global_scope_permission_shows_entry(app, client):
    with app.app_context():
        user = make_user()
        permission = make_permission("core.organization.read")
        grant_user_permission(user, permission, ScopeType.GLOBAL, None)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/navigation", headers=headers)
    keys = {item["key"] for item in resp.get_json()["data"]["navigation"]}
    assert "organizations" in keys


def test_me_navigation_delegation_shaped_grant_shows_entry(app, client):
    with app.app_context():
        team = make_team(make_department(make_organization()))
        delegator = make_user()
        delegatee = make_user()
        permission = make_permission("tasks.task.assign", is_delegable=True)
        grant_user_permission(
            delegatee, permission, ScopeType.TEAM, team.id, granted_by=delegator
        )
        db.session.commit()
        headers = auth_headers(delegatee)

    resp = client.get("/api/me/navigation", headers=headers)
    keys = {item["key"] for item in resp.get_json()["data"]["navigation"]}
    assert "tasks" in keys


def test_me_navigation_does_not_leak_sensitive_fields(app, client):
    with app.app_context():
        user = make_user()
        permission = make_permission("tasks.task.read")
        grant_user_permission(user, permission, ScopeType.GLOBAL, None)
        db.session.commit()
        headers = auth_headers(user)

    resp = client.get("/api/me/navigation", headers=headers)
    body_text = resp.get_data(as_text=True)
    assert "password_hash" not in body_text
    assert "token_hash" not in body_text
