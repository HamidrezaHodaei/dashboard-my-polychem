"""
Delegation eligibility + lifecycle tests -- app/permissions/delegation.py.

Covers every required Phase 2 test-matrix item for delegation: allowed
delegation, non-delegable permission, unauthorized delegation (missing
`authz.grant.delegate`), cross-organization delegation blocked, self-
delegation blocked, privilege escalation (scope broader than held)
blocked, target-user-outside-scope blocked, revoked delegation
deactivating the grant, and -- the key regression named twice in
AUTHORIZATION.md -- a delegated grant to one user never leaking to
another user who shares that same role.
"""
import pytest

from app.core.authorization.models import ScopeType, UserPermissionScope
from app.permissions.delegation import can_delegate, create_delegation, revoke_delegation
from app.permissions.exceptions import DelegationDeniedError
from app.permissions.service import has_permission

from .factories import (
    add_team_member,
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


def _sales_fixture(app, *, assignee_delegable=True):
    """Builds the AUTHORIZATION.md §10 scenario D shape: a manager role
    with DEPARTMENT-scoped tasks.task.assign + authz.grant.delegate, a
    team under that department, and two users sharing a specialist role
    -- one of whom (the delegatee) is a member of the team."""
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    manager_role = make_role(name="sales_manager")
    specialist_role = make_role(name="sales_specialist")

    manager = make_user()
    assign_role(manager, manager_role)

    delegatee = make_user()
    other_specialist = make_user()  # shares specialist_role, must NOT gain anything
    assign_role(delegatee, specialist_role)
    assign_role(other_specialist, specialist_role)
    add_team_member(team, delegatee)
    # other_specialist deliberately NOT added to the team.

    assign_permission = make_permission("tasks.task.assign", is_delegable=assignee_delegable)
    delegate_authority = make_permission("authz.grant.delegate", is_delegable=False)

    grant_role_permission(manager_role, assign_permission, ScopeType.DEPARTMENT, dept.id)
    grant_role_permission(manager_role, delegate_authority, ScopeType.DEPARTMENT, dept.id)

    return {
        "org": org,
        "dept": dept,
        "team": team,
        "manager": manager,
        "delegatee": delegatee,
        "other_specialist": other_specialist,
        "assign_permission": assign_permission,
    }


def test_delegation_allowed_scenario_d(app):
    """AUTHORIZATION.md §10 scenario D."""
    f = _sales_fixture(app)

    delegation = create_delegation(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )

    assert delegation.id is not None
    assert delegation.revoked_at is None
    assert has_permission(f["delegatee"], "tasks.task.assign", ScopeType.TEAM, f["team"].id) is True


def test_delegated_permission_does_not_leak_to_role_mate(app):
    """The regression AUTHORIZATION.md calls out explicitly: 'کارشناس
    فروش role-mates of علی are unaffected -- they gained nothing.'"""
    f = _sales_fixture(app)

    create_delegation(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )

    assert has_permission(f["delegatee"], "tasks.task.assign", ScopeType.TEAM, f["team"].id) is True
    assert (
        has_permission(f["other_specialist"], "tasks.task.assign", ScopeType.TEAM, f["team"].id)
        is False
    )


def test_delegation_blocked_non_delegable(app):
    """AUTHORIZATION.md §10 scenario E."""
    f = _sales_fixture(app, assignee_delegable=False)

    result = can_delegate(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )
    assert result.allowed is False
    assert result.reason_code == "not_delegable"

    with pytest.raises(DelegationDeniedError):
        create_delegation(
            delegator=f["manager"],
            delegatee=f["delegatee"],
            permission_key="tasks.task.assign",
            scope_type=ScopeType.TEAM,
            scope_id=f["team"].id,
        )
    assert not has_permission(f["delegatee"], "tasks.task.assign", ScopeType.TEAM, f["team"].id)


def test_delegation_blocked_scope_escalation(app):
    """AUTHORIZATION.md §10 scenario F: delegating at a scope broader
    than the delegator's own held scope."""
    f = _sales_fixture(app)
    other_org = make_organization()

    result = can_delegate(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.ORGANIZATION,
        scope_id=other_org.id,
    )
    assert result.allowed is False
    assert result.reason_code == "scope_escalation"


def test_delegation_blocked_target_user_outside_scope(app):
    """AUTHORIZATION.md §10 scenario G: delegatee has no membership in
    the target team."""
    f = _sales_fixture(app)

    result = can_delegate(
        delegator=f["manager"],
        delegatee=f["other_specialist"],  # not a member of the team
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )
    assert result.allowed is False
    assert result.reason_code == "target_outside_scope"


def test_delegation_blocked_self_delegation(app):
    """AUTHORIZATION.md §10 scenario H -- checked independent of the
    other five checks."""
    f = _sales_fixture(app)

    result = can_delegate(
        delegator=f["manager"],
        delegatee=f["manager"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )
    assert result.allowed is False
    assert result.reason_code == "self_delegation"


def test_delegation_blocked_permission_not_held(app):
    f = _sales_fixture(app)
    other_permission = make_permission("finance.transaction.read", is_delegable=True)

    result = can_delegate(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="finance.transaction.read",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )
    assert result.allowed is False
    assert result.reason_code == "permission_not_held"


def test_delegation_blocked_missing_delegation_authority(app):
    """Delegator holds the permission and it's delegable, but they do
    NOT hold `authz.grant.delegate` -- delegation is itself a permission
    +scope-checked action, not a bypass (AUTHORIZATION.md §6.5)."""
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    manager_role = make_role(name="sales_manager_no_delegate_authority")
    manager = make_user()
    assign_role(manager, manager_role)

    delegatee = make_user()
    add_team_member(team, delegatee)

    assign_permission = make_permission("tasks.task.assign", is_delegable=True)
    grant_role_permission(manager_role, assign_permission, ScopeType.DEPARTMENT, dept.id)
    # Deliberately no authz.grant.delegate grant for this manager.
    make_permission("authz.grant.delegate", is_delegable=False)

    result = can_delegate(
        delegator=manager,
        delegatee=delegatee,
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=team.id,
    )
    assert result.allowed is False
    assert result.reason_code == "delegation_authority_missing"


def test_cross_organization_delegation_blocked(app):
    """A manager scoped to DEPARTMENT in org A can never delegate into a
    department that belongs to org B -- scope_covers only matches through
    the real hierarchy, so this is blocked at the scope-containment
    check itself (reason_code == 'scope_escalation'), not a separate ad
    hoc org-boundary check."""
    f = _sales_fixture(app)
    other_org = make_organization()
    other_dept = make_department(other_org)
    other_team = make_team(other_dept)
    add_team_member(other_team, f["delegatee"])

    result = can_delegate(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=other_team.id,
    )
    assert result.allowed is False
    assert result.reason_code == "scope_escalation"


def test_delegation_via_user_level_grant_also_counts_for_possession(app):
    """§6.1: possession counts 'via role grant or user grant -- either
    counts'."""
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    manager = make_user()
    delegatee = make_user()
    add_team_member(team, delegatee)

    assign_permission = make_permission("tasks.task.assign", is_delegable=True)
    delegate_authority = make_permission("authz.grant.delegate", is_delegable=False)

    # Manager holds both permissions via direct USER grants, not a role.
    grant_user_permission(manager, assign_permission, ScopeType.DEPARTMENT, dept.id)
    grant_user_permission(manager, delegate_authority, ScopeType.DEPARTMENT, dept.id)

    result = can_delegate(
        delegator=manager,
        delegatee=delegatee,
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=team.id,
    )
    assert result.allowed is True


def test_revoked_delegation_deactivates_grant(app):
    f = _sales_fixture(app)

    delegation = create_delegation(
        delegator=f["manager"],
        delegatee=f["delegatee"],
        permission_key="tasks.task.assign",
        scope_type=ScopeType.TEAM,
        scope_id=f["team"].id,
    )
    assert has_permission(f["delegatee"], "tasks.task.assign", ScopeType.TEAM, f["team"].id) is True

    revoke_delegation(delegation=delegation, revoked_by=f["manager"])

    assert delegation.revoked_at is not None
    assert delegation.revoked_by_user_id == f["manager"].id
    assert (
        has_permission(f["delegatee"], "tasks.task.assign", ScopeType.TEAM, f["team"].id) is False
    )
    # The row is retained for history, not deleted (DATABASE.md).
    from app.extensions import db

    row = (
        db.session.query(UserPermissionScope)
        .filter_by(id=delegation.resulting_user_permission_scope_id)
        .one()
    )
    assert row.is_active is False
