"""
HTTP tests for /api/authz/delegations -- Phase 4's wrapper around Phase
2's delegation engine (app/permissions/delegation.py).

Covers exactly what IMPLEMENTATION_PLAN.md's Phase 4 test list calls
for: an allowed delegation, all five eligibility-check failures (plus
the independent self-delegation guard), and a regression test proving a
delegated grant to one user does not leak to another user sharing the
same role.
"""
from app.core.authorization.models import ScopeType, UserPermissionScope
from app.extensions import db
from tests.core4.factories import (
    add_team_member,
    assign_role,
    auth_headers,
    grant_role_permission,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_role,
    make_team,
    make_user,
)

DELEGATE_KEY = "authz.grant.delegate"


def _delegator_with_authority(
    permission_key: str, scope_type: ScopeType, scope_id: int | None, *, is_delegable: bool = True
):
    """A user who holds `permission_key` (delegable) at `scope`, plus
    `authz.grant.delegate` at the same scope -- everything check 1-3-2-5
    need, so the test only has to break ONE thing per scenario."""
    delegator = make_user()
    target_permission = make_permission(permission_key, is_delegable=is_delegable)
    grant_user_permission(delegator, target_permission, scope_type, scope_id)
    authority_permission = make_permission(DELEGATE_KEY, is_delegable=False)
    grant_user_permission(delegator, authority_permission, scope_type, scope_id)
    return delegator


def _post_delegation(client, headers, *, delegatee_id, permission_key, scope_type, scope_id=None):
    return client.post(
        "/api/authz/delegations",
        json={
            "delegatee_user_id": delegatee_id,
            "permission_key": permission_key,
            "scope_type": scope_type,
            "scope_id": scope_id,
        },
        headers=headers,
    )


def test_allowed_delegation_full(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = _delegator_with_authority(
            "core.user.read", ScopeType.DEPARTMENT, dept.id, is_delegable=True
        )
        delegatee = make_user(department_id=dept.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_id = dept.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["delegatee_user_id"] == delegatee_id
    assert body["revoked_at"] is None


def test_self_delegation_blocked(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = _delegator_with_authority("core.user.read", ScopeType.DEPARTMENT, dept.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegator_id = delegator.id
        dept_id = dept.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegator_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    assert resp.status_code == 403


def test_blocked_permission_not_held(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = make_user()  # holds nothing
        # authority alone, but not the permission itself
        authority = make_permission(DELEGATE_KEY)
        grant_user_permission(delegator, authority, ScopeType.DEPARTMENT, dept.id)
        make_permission("core.user.read", is_delegable=True)
        delegatee = make_user(department_id=dept.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_id = dept.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    assert resp.status_code == 403


def test_blocked_not_delegable(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        # core.role.read is never delegable per the registry's rules,
        # but this test builds its own local permission row too so it's
        # explicit and not dependent on registry defaults.
        delegator = _delegator_with_authority(
            "core.role.read", ScopeType.DEPARTMENT, dept.id, is_delegable=False
        )
        delegatee = make_user(department_id=dept.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_id = dept.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.role.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    assert resp.status_code == 403


def test_blocked_scope_escalation(client, app):
    """Delegator holds the permission at DEPARTMENT scope but tries to
    delegate it at the broader ORGANIZATION scope."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = _delegator_with_authority("core.user.read", ScopeType.DEPARTMENT, dept.id)
        delegatee = make_user(organization_id=org.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        org_id = org.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="ORGANIZATION", scope_id=org_id,
    )
    assert resp.status_code == 403


def test_blocked_target_outside_scope(client, app):
    """Delegatee does not actually belong to the target department."""
    with app.app_context():
        org = make_organization()
        dept_a = make_department(org)
        dept_b = make_department(org)
        delegator = _delegator_with_authority("core.user.read", ScopeType.DEPARTMENT, dept_a.id)
        delegatee = make_user(department_id=dept_b.id)  # wrong department
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_a_id = dept_a.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_a_id,
    )
    assert resp.status_code == 403


def test_blocked_delegation_authority_missing(client, app):
    """Delegator holds the target permission itself but NOT
    authz.grant.delegate covering that scope."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = make_user()
        target_permission = make_permission("core.user.read", is_delegable=True)
        grant_user_permission(delegator, target_permission, ScopeType.DEPARTMENT, dept.id)
        # authz.grant.delegate row exists but is NOT granted to delegator
        make_permission(DELEGATE_KEY)
        delegatee = make_user(department_id=dept.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_id = dept.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    assert resp.status_code == 403


def test_revoke_delegation_by_delegator(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = _delegator_with_authority("core.user.read", ScopeType.DEPARTMENT, dept.id)
        delegatee = make_user(department_id=dept.id)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_id = dept.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    delegation_id = resp.get_json()["data"]["id"]

    resp = client.post(f"/api/authz/delegations/{delegation_id}/revoke", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["revoked_at"] is not None

    scope = db.session.query(UserPermissionScope).filter_by(user_id=delegatee_id).one()
    assert scope.is_active is False


def test_revoke_denied_for_unrelated_user(client, app):
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = _delegator_with_authority("core.user.read", ScopeType.DEPARTMENT, dept.id)
        delegatee = make_user(department_id=dept.id)
        bystander = make_user()
        db.session.commit()
        delegator_headers = auth_headers(delegator)
        bystander_headers = auth_headers(bystander)
        delegatee_id = delegatee.id
        dept_id = dept.id

    resp = _post_delegation(
        client, delegator_headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    delegation_id = resp.get_json()["data"]["id"]

    resp = client.post(
        f"/api/authz/delegations/{delegation_id}/revoke", headers=bystander_headers
    )
    assert resp.status_code == 403


def test_delegated_grant_does_not_leak_to_role_mate(client, app):
    """Regression: a delegated grant is a USER-level grant on the
    delegatee specifically -- another user sharing the same ROLE as the
    delegatee must not gain it."""
    with app.app_context():
        org = make_organization()
        dept = make_department(org)
        delegator = _delegator_with_authority("core.user.read", ScopeType.DEPARTMENT, dept.id)
        shared_role = make_role()
        delegatee = make_user(department_id=dept.id)
        role_mate = make_user(department_id=dept.id)
        assign_role(delegatee, shared_role)
        assign_role(role_mate, shared_role)
        db.session.commit()
        headers = auth_headers(delegator)
        delegatee_id = delegatee.id
        dept_id = dept.id
        role_mate_headers_user_id = role_mate.id

    resp = _post_delegation(
        client, headers,
        delegatee_id=delegatee_id, permission_key="core.user.read",
        scope_type="DEPARTMENT", scope_id=dept_id,
    )
    assert resp.status_code == 201

    from app.core.users.models import User
    from app.permissions.service import has_permission

    delegatee_obj = db.session.get(User, delegatee_id)
    role_mate_obj = db.session.get(User, role_mate_headers_user_id)

    assert has_permission(delegatee_obj, "core.user.read", ScopeType.DEPARTMENT, dept_id) is True
    assert has_permission(role_mate_obj, "core.user.read", ScopeType.DEPARTMENT, dept_id) is False
