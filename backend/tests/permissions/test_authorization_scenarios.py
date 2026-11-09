"""
Direct reproduction of every worked scenario in AUTHORIZATION.md §10
(A-J), using the permission keys AUTHORIZATION.md itself uses for these
scenarios (`tasks.task.*`, `finance.transaction.read`, `users.user.delete`,
`authz.grant.delegate`). These are the documentation's own illustrative
examples, used here only as test fixtures to prove the engine reproduces
the documented behavior -- they are not added to app/permissions/registry.py
(see that module's docstring for why).

Scenarios D-H (the delegation-specific ones) are covered in
test_delegation.py; this file covers A, B, C, I, J plus the two general
rules stated alongside them.
"""
from app.core.authorization.models import ScopeType
from app.core.teams.models import TeamMember
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


def test_scenario_a_role_grant_in_scope_allowed(app):
    """مدیر فروش (role grant, DEPARTMENT: فروش) creating a task with
    department_id=فروش, team_id=فروش داخلی. Steps 1-2 (this module's
    scope) pass; step 3 does not apply to a create action with no
    pre-existing resource to own."""
    org = make_organization()
    sales_dept = make_department(org)
    inside_sales_team = make_team(sales_dept)

    manager_role = make_role(name="sales_manager")
    manager = make_user()
    assign_role(manager, manager_role)

    create_permission = make_permission("tasks.task.create")
    grant_role_permission(manager_role, create_permission, ScopeType.DEPARTMENT, sales_dept.id)

    assert has_permission(manager, "tasks.task.create", ScopeType.DEPARTMENT, sales_dept.id) is True
    # The DEPARTMENT grant also naturally covers the team underneath it.
    assert has_permission(manager, "tasks.task.create", ScopeType.TEAM, inside_sales_team.id) is True


def test_scenario_b_role_grant_out_of_scope_denied(app):
    """Same user attempts department_id=مالی -- step 1 passes, step 2
    fails (no grant covers مالی)."""
    org = make_organization()
    sales_dept = make_department(org)
    finance_dept = make_department(org)

    manager_role = make_role(name="sales_manager")
    manager = make_user()
    assign_role(manager, manager_role)

    create_permission = make_permission("tasks.task.create")
    grant_role_permission(manager_role, create_permission, ScopeType.DEPARTMENT, sales_dept.id)

    assert has_permission(manager, "tasks.task.create", ScopeType.DEPARTMENT, sales_dept.id) is True
    assert has_permission(manager, "tasks.task.create", ScopeType.DEPARTMENT, finance_dept.id) is False


def test_scenario_c_permission_never_held_denied(app):
    """Same user attempts finance.transaction.read -- step 1 fails outright."""
    org = make_organization()
    sales_dept = make_department(org)

    manager_role = make_role(name="sales_manager")
    manager = make_user()
    assign_role(manager, manager_role)

    create_permission = make_permission("tasks.task.create")
    grant_role_permission(manager_role, create_permission, ScopeType.DEPARTMENT, sales_dept.id)
    make_permission("finance.transaction.read")  # exists, but never granted to manager

    assert has_permission(manager, "finance.transaction.read") is False


def test_scenario_i_mixed_source_check_with_step_3_membership(app):
    """علی (holding a user-level grant) assigns a task whose team_id
    matches his grant to a teammate who is a member of that team. Steps
    1-2 pass via the user grant; step 3 (assignee must be a team member)
    is a generic team_members lookup, composable on top of this engine
    without needing a Task model yet."""
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    ali = make_user()
    teammate = make_user()
    outsider = make_user()
    add_team_member(team, ali)
    add_team_member(team, teammate)
    # outsider deliberately not on the team

    assign_permission = make_permission("tasks.task.assign")
    grant_user_permission(ali, assign_permission, ScopeType.TEAM, team.id)

    # Steps 1-2: علی holds tasks.task.assign covering this team.
    assert has_permission(ali, "tasks.task.assign", ScopeType.TEAM, team.id) is True

    # Step 3: assignee must actually be a member of the task's team.
    def is_team_member(user_id, team_id):
        from app.extensions import db

        return (
            db.session.query(TeamMember)
            .filter_by(team_id=team_id, user_id=user_id)
            .first()
            is not None
        )

    assert is_team_member(teammate.id, team.id) is True
    assert is_team_member(outsider.id, team.id) is False


def test_scenario_j_admin_global_role_unrestricted(app):
    """`admin` role holds all permissions at GLOBAL scope; every step
    passes for any resource -- mirrors the actual seeded
    admin | system.platform.manage | GLOBAL grant from Phase 1, plus an
    arbitrary additional permission to prove it's not special-cased to
    one key."""
    admin_role = make_role(name="admin")
    admin_user = make_user()
    assign_role(admin_user, admin_role)

    seeded_permission = make_permission("system.platform.manage")
    grant_role_permission(admin_role, seeded_permission, ScopeType.GLOBAL)

    arbitrary_permission = make_permission("users.user.delete")
    grant_role_permission(admin_role, arbitrary_permission, ScopeType.GLOBAL)

    org = make_organization()
    dept = make_department(org)

    assert has_permission(admin_user, "system.platform.manage") is True
    assert has_permission(admin_user, "users.user.delete", ScopeType.DEPARTMENT, dept.id) is True
