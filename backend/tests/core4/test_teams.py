"""HTTP tests for /api/core/teams -- Phase 4."""
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


def test_create_team_requires_department_scope(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        user = make_user()
        _grant(user, "core.team.create", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(user)
        dept_id = dept.id

    resp = client.post(
        "/api/core/teams", json={"name": "New Team", "department_id": dept_id}, headers=headers
    )
    assert resp.status_code == 201


def test_add_and_remove_team_member(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        member = make_user()
        manager = make_user()
        _grant(manager, "core.team.update", ScopeType.TEAM, team.id)
        db.session.commit()
        headers = auth_headers(manager)
        team_id, member_id = team.id, member.id

    resp = client.post(
        f"/api/core/teams/{team_id}/members", json={"user_id": member_id}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.get_json()["data"]["user_id"] == member_id

    # duplicate add is rejected
    resp = client.post(
        f"/api/core/teams/{team_id}/members", json={"user_id": member_id}, headers=headers
    )
    assert resp.status_code == 409

    resp = client.delete(f"/api/core/teams/{team_id}/members/{member_id}", headers=headers)
    assert resp.status_code == 200

    # removing again is a 404 (no longer a member)
    resp = client.delete(f"/api/core/teams/{team_id}/members/{member_id}", headers=headers)
    assert resp.status_code == 404


def test_list_team_members(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        member = make_user()
        manager = make_user()
        _grant(manager, "core.team.update", ScopeType.TEAM, team.id)
        _grant(manager, "core.team.read", ScopeType.TEAM, team.id)
        db.session.commit()
        headers = auth_headers(manager)
        team_id, member_id = team.id, member.id

    client.post(f"/api/core/teams/{team_id}/members", json={"user_id": member_id}, headers=headers)

    resp = client.get(f"/api/core/teams/{team_id}/members", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body) == 1
    assert body[0]["user_id"] == member_id


def test_team_membership_management_requires_team_update_permission(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        team = make_team(dept)
        member = make_user()
        bystander = make_user()  # no grants at all
        db.session.commit()
        headers = auth_headers(bystander)
        team_id, member_id = team.id, member.id

    resp = client.post(
        f"/api/core/teams/{team_id}/members", json={"user_id": member_id}, headers=headers
    )
    assert resp.status_code == 403
