"""
Effective grants resolution tests -- app/permissions/service.py.

Covers: role grant, direct user grant, both sources unioned with no
precedence, inactive role grant excluded, inactive user grant excluded,
inactive role itself excluded, and scope-checked has_permission() across
GLOBAL/ORGANIZATION/DEPARTMENT/TEAM/SELF.
"""
from app.core.authorization.models import ScopeType
from app.permissions.service import get_effective_grants, has_permission

from .factories import (
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


def test_role_grant_is_effective(app):
    user = make_user()
    role = make_role()
    assign_role(user, role)
    permission = make_permission("tasks.task.read")
    grant_role_permission(role, permission, ScopeType.GLOBAL)

    assert has_permission(user, "tasks.task.read") is True


def test_direct_user_grant_is_effective(app):
    user = make_user()
    permission = make_permission("tasks.task.read")
    grant_user_permission(user, permission, ScopeType.GLOBAL)

    assert has_permission(user, "tasks.task.read") is True


def test_role_and_user_grants_are_unioned_with_no_precedence(app):
    """A permission held via a role and the same permission held via a
    direct user grant are equivalent once resolved (AUTHORIZATION.md
    §5's worked example)."""
    user = make_user()
    role = make_role()
    assign_role(user, role)
    dept_permission = make_permission("tasks.task.create")
    team_permission = make_permission("tasks.task.assign", is_delegable=True)

    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    grant_role_permission(role, dept_permission, ScopeType.DEPARTMENT, dept.id)
    grant_user_permission(user, team_permission, ScopeType.TEAM, team.id)

    grants = get_effective_grants(user)
    keys = {g.permission_key for g in grants}
    assert keys == {"tasks.task.create", "tasks.task.assign"}
    assert has_permission(user, "tasks.task.create", ScopeType.DEPARTMENT, dept.id) is True
    assert has_permission(user, "tasks.task.assign", ScopeType.TEAM, team.id) is True


def test_permission_never_held_denied(app):
    user = make_user()
    assert has_permission(user, "finance.transaction.read") is False


def test_inactive_role_permission_scope_excluded(app):
    user = make_user()
    role = make_role()
    assign_role(user, role)
    permission = make_permission("tasks.task.read")
    grant_role_permission(role, permission, ScopeType.GLOBAL, is_active=False)

    assert has_permission(user, "tasks.task.read") is False


def test_inactive_user_permission_scope_excluded(app):
    user = make_user()
    permission = make_permission("tasks.task.read")
    grant_user_permission(user, permission, ScopeType.GLOBAL, is_active=False)

    assert has_permission(user, "tasks.task.read") is False


def test_inactive_role_excludes_its_grants(app):
    """AUTHORIZATION.md §5: 'via user's active roles' -- an inactive
    role's grants must not count even if the RolePermissionScope row
    itself is still active."""
    user = make_user()
    role = make_role(is_active=False)
    assign_role(user, role)
    permission = make_permission("tasks.task.read")
    grant_role_permission(role, permission, ScopeType.GLOBAL, is_active=True)

    assert has_permission(user, "tasks.task.read") is False


def test_scope_check_department_scope(app):
    user = make_user()
    role = make_role()
    assign_role(user, role)
    permission = make_permission("tasks.task.create")
    org = make_organization()
    dept = make_department(org)
    other_dept = make_department(org)
    grant_role_permission(role, permission, ScopeType.DEPARTMENT, dept.id)

    assert has_permission(user, "tasks.task.create", ScopeType.DEPARTMENT, dept.id) is True
    assert has_permission(user, "tasks.task.create", ScopeType.DEPARTMENT, other_dept.id) is False


def test_scope_check_team_scope_via_department_grant(app):
    """A DEPARTMENT grant naturally covers the teams underneath it --
    'no per-team grant needed' (AUTHORIZATION.md §7)."""
    user = make_user()
    role = make_role()
    assign_role(user, role)
    permission = make_permission("tasks.task.assign")
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)
    grant_role_permission(role, permission, ScopeType.DEPARTMENT, dept.id)

    assert has_permission(user, "tasks.task.assign", ScopeType.TEAM, team.id) is True


def test_scope_check_self_scope(app):
    user = make_user()
    permission = make_permission("tasks.task.read")
    grant_user_permission(user, permission, ScopeType.SELF)

    assert has_permission(user, "tasks.task.read", ScopeType.SELF, None) is True


def test_scope_check_organization_scope(app):
    user = make_user()
    role = make_role()
    assign_role(user, role)
    permission = make_permission("tasks.analytics.read")
    org = make_organization()
    other_org = make_organization()
    grant_role_permission(role, permission, ScopeType.ORGANIZATION, org.id)

    assert has_permission(user, "tasks.analytics.read", ScopeType.ORGANIZATION, org.id) is True
    assert has_permission(user, "tasks.analytics.read", ScopeType.ORGANIZATION, other_org.id) is False
