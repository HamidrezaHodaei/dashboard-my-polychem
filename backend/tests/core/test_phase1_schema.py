"""
Phase 1 database/model tests — organizational hierarchy, identity, and the
RBAC/grant tables, per IMPLEMENTATION_PLAN.md Phase 1's test checklist:
organizations, departments, teams, team membership, users, roles,
permissions, user-role assignment, role permission scopes, user permission
scopes, delegation relationships, audit log relationships, and important
unique constraints / foreign keys.

Runs entirely against SQLite (TestingConfig, see tests/conftest.py) — no
live MySQL server required. FK enforcement on SQLite is turned on via the
PRAGMA listener in app/extensions.py specifically so the FK tests here are
meaningful (SQLite ignores FK constraints by default otherwise).

No permission *evaluation* is tested here — there is no engine yet
(Phase 2). These tests only prove the schema stores what DATABASE.md and
AUTHORIZATION.md say it should, with the right constraints.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.core.organizations.models import Organization
from app.core.departments.models import Department
from app.core.teams.models import Team, TeamMember
from app.core.users.models import User
from app.core.roles.models import Role
from app.core.permissions.models import Permission
from app.core.authorization.models import (
    UserRole,
    RolePermissionScope,
    UserPermissionScope,
    Delegation,
    ScopeType,
)
from app.core.audit_logs.models import AuditLog


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def make_user(**overrides):
    defaults = dict(
        full_name="Test User",
        email=f"user{id(overrides)}@example.com",
        username=f"user{id(overrides)}",
        password_hash="not-a-real-hash",
    )
    defaults.update(overrides)
    user = User(**defaults)
    db.session.add(user)
    db.session.flush()
    return user


# ---------------------------------------------------------------------
# organizations
# ---------------------------------------------------------------------
def test_organization_create_and_defaults(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.commit()

    assert org.id is not None
    assert org.is_active is True
    assert org.deleted_at is None
    assert org.parent_organization_id is None


def test_organization_self_referential_parent(app):
    parent = Organization(name="دفتر مرکزی")
    db.session.add(parent)
    db.session.flush()

    child = Organization(name="شعبه تهران", parent_organization_id=parent.id)
    db.session.add(child)
    db.session.commit()

    assert child.parent.id == parent.id
    assert child in parent.children


# ---------------------------------------------------------------------
# departments
# ---------------------------------------------------------------------
def test_department_belongs_to_organization(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()

    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.commit()

    assert dept.organization.id == org.id
    assert dept in org.departments


def test_department_manager_user_id_is_not_authorization(app):
    """
    Structural check only: manager_user_id is a plain informational FK,
    not a permission grant of any kind — asserting that setting it does
    not create any row in either grant table (role_permission_scopes /
    user_permission_scopes). See AUTHORIZATION.md §2.
    """
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()

    manager = make_user(email="manager@example.com", username="manager1")
    dept = Department(name="فروش", organization_id=org.id, manager_user_id=manager.id)
    db.session.add(dept)
    db.session.commit()

    assert dept.manager.id == manager.id
    assert db.session.query(RolePermissionScope).count() == 0
    assert db.session.query(UserPermissionScope).count() == 0


def test_department_organization_id_foreign_key_enforced(app):
    dept = Department(name="فروش", organization_id=999999)
    db.session.add(dept)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------
# teams
# ---------------------------------------------------------------------
def test_team_belongs_to_department(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()

    team = Team(name="فروش داخلی", department_id=dept.id)
    db.session.add(team)
    db.session.commit()

    assert team.department.id == dept.id
    assert team in dept.teams


def test_team_department_id_foreign_key_enforced(app):
    team = Team(name="فروش داخلی", department_id=999999)
    db.session.add(team)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------
# team membership
# ---------------------------------------------------------------------
def test_team_membership_many_to_many(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()
    team = Team(name="فروش داخلی", department_id=dept.id)
    db.session.add(team)
    db.session.flush()

    user = make_user(email="ali@example.com", username="ali")
    membership = TeamMember(team_id=team.id, user_id=user.id)
    db.session.add(membership)
    db.session.commit()

    assert membership in team.members
    assert membership in user.team_memberships


def test_team_membership_unique_constraint(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()
    team = Team(name="فروش داخلی", department_id=dept.id)
    db.session.add(team)
    db.session.flush()
    user = make_user(email="ali2@example.com", username="ali2")

    db.session.add(TeamMember(team_id=team.id, user_id=user.id))
    db.session.commit()

    db.session.add(TeamMember(team_id=team.id, user_id=user.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_team_membership_does_not_grant_anything(app):
    """
    Placing a user in a department AND on a team must grant nothing by
    itself — IMPLEMENTATION_PLAN.md Phase 1's explicit test requirement.
    """
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()
    team = Team(name="فروش داخلی", department_id=dept.id)
    db.session.add(team)
    db.session.flush()

    user = make_user(email="newhire@example.com", username="newhire", department_id=dept.id)
    db.session.add(TeamMember(team_id=team.id, user_id=user.id))
    db.session.commit()

    # Placed in a department AND a team — but holds zero roles and zero
    # direct grants. Organizational placement and authorization are
    # independent, as AUTHORIZATION.md §2 requires.
    assert user.department_id == dept.id
    assert db.session.query(UserRole).filter_by(user_id=user.id).count() == 0
    assert db.session.query(UserPermissionScope).filter_by(user_id=user.id).count() == 0


# ---------------------------------------------------------------------
# users
# ---------------------------------------------------------------------
def test_user_create_and_defaults(app):
    user = make_user(email="basic@example.com", username="basicuser")
    db.session.commit()

    assert user.id is not None
    assert user.is_active is True
    assert user.organization_id is None
    assert user.department_id is None


def test_user_email_unique_constraint(app):
    make_user(email="dupe@example.com", username="dupe1")
    db.session.commit()

    db.session.add(
        User(
            full_name="Another",
            email="dupe@example.com",
            username="dupe2",
            password_hash="x",
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_user_username_unique_constraint(app):
    make_user(email="uniq1@example.com", username="sameusername")
    db.session.commit()

    db.session.add(
        User(
            full_name="Another",
            email="uniq2@example.com",
            username="sameusername",
            password_hash="x",
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_user_placement_independent_of_role(app):
    """
    Model-level version of IMPLEMENTATION_PLAN.md Phase 1's required test:
    create a department under an organization, place a user via
    department_id, separately assign a role, confirm the two are
    independent — placing a user in a department grants nothing by itself.
    """
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()

    user = make_user(email="placed@example.com", username="placed", department_id=dept.id)
    db.session.commit()

    # Placement alone: no role held yet.
    assert db.session.query(UserRole).filter_by(user_id=user.id).count() == 0

    role = Role(name="sales_specialist", display_name="کارشناس فروش", is_system_role=True)
    db.session.add(role)
    db.session.flush()
    db.session.add(UserRole(user_id=user.id, role_id=role.id))
    db.session.commit()

    # Assigning the role is a separate act from placement; both are now
    # true independently of one another.
    assert user.department_id == dept.id
    assert db.session.query(UserRole).filter_by(user_id=user.id, role_id=role.id).count() == 1


# ---------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------
def test_role_create_and_defaults(app):
    role = Role(name="sales_manager", display_name="مدیر فروش", is_system_role=True)
    db.session.add(role)
    db.session.commit()

    assert role.id is not None
    assert role.is_active is True
    assert role.is_system_role is True


def test_role_name_unique_constraint(app):
    db.session.add(Role(name="admin", display_name="Admin"))
    db.session.commit()

    db.session.add(Role(name="admin", display_name="Admin Duplicate"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------
# permissions
# ---------------------------------------------------------------------
def test_permission_create_and_defaults(app):
    perm = Permission(
        key="tasks.task.assign", module="tasks", resource="task", action="assign"
    )
    db.session.add(perm)
    db.session.commit()

    assert perm.id is not None
    assert perm.is_delegable is False  # default per DATABASE.md


def test_permission_key_unique_constraint(app):
    db.session.add(
        Permission(key="tasks.task.read", module="tasks", resource="task", action="read")
    )
    db.session.commit()

    db.session.add(
        Permission(key="tasks.task.read", module="tasks", resource="task", action="read")
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ---------------------------------------------------------------------
# user-role assignment
# ---------------------------------------------------------------------
def test_user_role_assignment(app):
    user = make_user(email="ur@example.com", username="ur_user")
    role = Role(name="finance_specialist", display_name="کارشناس مالی", is_system_role=True)
    db.session.add(role)
    db.session.flush()

    assignment = UserRole(user_id=user.id, role_id=role.id)
    db.session.add(assignment)
    db.session.commit()

    assert assignment.user.id == user.id
    assert assignment.role.id == role.id
    assert assignment.organization_id is None


def test_user_role_optionally_scoped_to_organization(app):
    org = Organization(name="کارخانه")
    db.session.add(org)
    db.session.flush()
    user = make_user(email="ur2@example.com", username="ur_user2")
    role = Role(name="factory_manager", display_name="مدیر کارخانه", is_system_role=True)
    db.session.add(role)
    db.session.flush()

    assignment = UserRole(user_id=user.id, role_id=role.id, organization_id=org.id)
    db.session.add(assignment)
    db.session.commit()

    assert assignment.organization.id == org.id


# ---------------------------------------------------------------------
# role_permission_scopes
# ---------------------------------------------------------------------
def test_role_permission_scope_department_grant(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()

    role = Role(name="sales_manager", display_name="مدیر فروش", is_system_role=True)
    perm = Permission(
        key="tasks.task.create", module="tasks", resource="task", action="create"
    )
    db.session.add_all([role, perm])
    db.session.flush()

    grant = RolePermissionScope(
        role_id=role.id,
        permission_id=perm.id,
        scope_type=ScopeType.DEPARTMENT,
        scope_id=dept.id,
    )
    db.session.add(grant)
    db.session.commit()

    assert grant.is_active is True
    assert grant.scope_type == ScopeType.DEPARTMENT
    assert grant.scope_id == dept.id
    assert grant.granted_by_user_id is None  # NULL allowed for seed-time grants


def test_role_permission_scope_global_grant_scope_id_nullable(app):
    role = Role(name="admin", display_name="Admin", is_system_role=True)
    perm = Permission(key="system.platform.manage", module="system", resource="platform", action="manage")
    db.session.add_all([role, perm])
    db.session.flush()

    grant = RolePermissionScope(
        role_id=role.id, permission_id=perm.id, scope_type=ScopeType.GLOBAL, scope_id=None
    )
    db.session.add(grant)
    db.session.commit()

    assert grant.scope_id is None


# ---------------------------------------------------------------------
# user_permission_scopes
# ---------------------------------------------------------------------
def test_user_permission_scope_is_additional_to_role(app):
    """
    Reproduces AUTHORIZATION.md §4's worked example structurally: two
    users share the same role (کارشناس فروش); only one of them
    additionally holds a direct user_permission_scopes grant. The other
    role-mate must not be affected.
    """
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()
    team = Team(name="فروش داخلی", department_id=dept.id)
    db.session.add(team)
    db.session.flush()

    role = Role(name="sales_specialist", display_name="کارشناس فروش", is_system_role=True)
    perm = Permission(
        key="tasks.task.assign", module="tasks", resource="task", action="assign", is_delegable=True
    )
    db.session.add_all([role, perm])
    db.session.flush()

    ali = make_user(email="ali3@example.com", username="ali3")
    reza = make_user(email="reza@example.com", username="reza")
    db.session.add(UserRole(user_id=ali.id, role_id=role.id))
    db.session.add(UserRole(user_id=reza.id, role_id=role.id))
    db.session.flush()

    # Only Ali gets the direct, targeted grant.
    grant = UserPermissionScope(
        user_id=ali.id,
        permission_id=perm.id,
        scope_type=ScopeType.TEAM,
        scope_id=team.id,
    )
    db.session.add(grant)
    db.session.commit()

    assert db.session.query(UserPermissionScope).filter_by(user_id=ali.id).count() == 1
    # Reza holds the same role but gained nothing extra.
    assert db.session.query(UserPermissionScope).filter_by(user_id=reza.id).count() == 0


def test_user_permission_scope_revocation_sets_inactive_not_deleted(app):
    perm = Permission(key="tasks.task.read", module="tasks", resource="task", action="read")
    user = make_user(email="revoke@example.com", username="revokeuser")
    db.session.add(perm)
    db.session.flush()

    grant = UserPermissionScope(
        user_id=user.id, permission_id=perm.id, scope_type=ScopeType.SELF
    )
    db.session.add(grant)
    db.session.commit()

    grant.is_active = False
    db.session.commit()

    # Row retained for history — not deleted — per DATABASE.md.
    persisted = db.session.get(UserPermissionScope, grant.id)
    assert persisted is not None
    assert persisted.is_active is False


# ---------------------------------------------------------------------
# delegation relationships
# ---------------------------------------------------------------------
def test_delegation_full_lifecycle_record(app):
    delegator = make_user(email="delegator@example.com", username="delegator")
    delegatee = make_user(email="delegatee@example.com", username="delegatee")
    perm = Permission(
        key="tasks.task.assign", module="tasks", resource="task", action="assign", is_delegable=True
    )
    db.session.add(perm)
    db.session.flush()

    grant = UserPermissionScope(
        user_id=delegatee.id,
        permission_id=perm.id,
        scope_type=ScopeType.TEAM,
        scope_id=1,
        granted_by_user_id=delegator.id,
    )
    db.session.add(grant)
    db.session.flush()

    delegation = Delegation(
        delegator_user_id=delegator.id,
        delegatee_user_id=delegatee.id,
        resulting_user_permission_scope_id=grant.id,
    )
    db.session.add(delegation)
    db.session.commit()

    assert delegation.delegator.id == delegator.id
    assert delegation.delegatee.id == delegatee.id
    assert delegation.resulting_user_permission_scope.id == grant.id
    assert delegation.revoked_at is None
    assert delegation.revoked_by_user_id is None


def test_delegation_revocation_fields(app):
    delegator = make_user(email="delegator2@example.com", username="delegator2")
    delegatee = make_user(email="delegatee2@example.com", username="delegatee2")
    admin = make_user(email="admin_revoker@example.com", username="admin_revoker")
    perm = Permission(key="tasks.task.read", module="tasks", resource="task", action="read", is_delegable=True)
    db.session.add(perm)
    db.session.flush()

    grant = UserPermissionScope(
        user_id=delegatee.id, permission_id=perm.id, scope_type=ScopeType.SELF
    )
    db.session.add(grant)
    db.session.flush()

    delegation = Delegation(
        delegator_user_id=delegator.id,
        delegatee_user_id=delegatee.id,
        resulting_user_permission_scope_id=grant.id,
    )
    db.session.add(delegation)
    db.session.commit()

    # Revoke: service-layer logic (Phase 2+) would set both of these in
    # one transaction; this test only proves the schema can represent it.
    from datetime import datetime, timezone

    delegation.revoked_at = datetime.now(timezone.utc)
    delegation.revoked_by_user_id = admin.id
    grant.is_active = False
    db.session.commit()

    assert delegation.revoked_at is not None
    assert delegation.revoked_by_user_id == admin.id
    assert delegation.resulting_user_permission_scope.is_active is False


def test_delegation_self_delegation_not_blocked_by_schema(app):
    """
    DATABASE.md's privilege-escalation notes are explicit: the schema does
    NOT block delegator_user_id == delegatee_user_id — that guard is a
    Phase 2 service-layer rule (AUTHORIZATION.md §9), not a DB constraint.
    This test documents that fact so nobody mistakes its absence for a bug.
    """
    user = make_user(email="selfdelegate@example.com", username="selfdelegate")
    perm = Permission(key="tasks.task.read", module="tasks", resource="task", action="read", is_delegable=True)
    db.session.add(perm)
    db.session.flush()

    grant = UserPermissionScope(
        user_id=user.id, permission_id=perm.id, scope_type=ScopeType.SELF
    )
    db.session.add(grant)
    db.session.flush()

    delegation = Delegation(
        delegator_user_id=user.id,
        delegatee_user_id=user.id,
        resulting_user_permission_scope_id=grant.id,
    )
    db.session.add(delegation)
    # No IntegrityError expected — the schema permits this row to exist.
    db.session.commit()

    assert delegation.delegator_user_id == delegation.delegatee_user_id


# ---------------------------------------------------------------------
# audit log relationships
# ---------------------------------------------------------------------
def test_audit_log_tied_to_user_action(app):
    user = make_user(email="auditor@example.com", username="auditor")
    entry = AuditLog(
        user_id=user.id,
        action="user.create",
        module="core.users",
        entity_type="User",
        entity_id=user.id,
        event_metadata={"changed_fields": ["email"]},
        ip_address="127.0.0.1",
    )
    db.session.add(entry)
    db.session.commit()

    assert entry.id is not None
    assert entry.user.id == user.id
    assert entry.event_metadata == {"changed_fields": ["email"]}


def test_audit_log_user_id_nullable_for_system_events(app):
    entry = AuditLog(user_id=None, action="system.startup", module="system")
    db.session.add(entry)
    db.session.commit()

    assert entry.id is not None
    assert entry.user is None


# ---------------------------------------------------------------------
# important foreign keys (beyond the department/team cases above)
# ---------------------------------------------------------------------
def test_user_role_user_id_foreign_key_enforced(app):
    role = Role(name="finance_manager", display_name="مدیر مالی", is_system_role=True)
    db.session.add(role)
    db.session.flush()

    db.session.add(UserRole(user_id=999999, role_id=role.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_delegation_resulting_grant_foreign_key_enforced(app):
    delegator = make_user(email="fk_delegator@example.com", username="fk_delegator")
    delegatee = make_user(email="fk_delegatee@example.com", username="fk_delegatee")
    db.session.add(
        Delegation(
            delegator_user_id=delegator.id,
            delegatee_user_id=delegatee.id,
            resulting_user_permission_scope_id=999999,
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_team_member_cascade_delete_on_team_removal(app):
    org = Organization(name="دفتر مرکزی")
    db.session.add(org)
    db.session.flush()
    dept = Department(name="فروش", organization_id=org.id)
    db.session.add(dept)
    db.session.flush()
    team = Team(name="فروش داخلی", department_id=dept.id)
    db.session.add(team)
    db.session.flush()
    user = make_user(email="cascade@example.com", username="cascadeuser")
    db.session.add(TeamMember(team_id=team.id, user_id=user.id))
    db.session.commit()

    team_id = team.id
    db.session.delete(team)
    db.session.commit()

    assert db.session.query(TeamMember).filter_by(team_id=team_id).count() == 0
