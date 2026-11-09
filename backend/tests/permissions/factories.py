"""
Shared test-data builders for Phase 2 permission-engine tests.

Plain helper functions (not fixtures) -- each commits nothing itself
(only flushes), leaving the calling test's transaction/session in
control, consistent with the existing Phase 1 test style
(tests/core/test_phase1_schema.py's `make_user`).
"""
import itertools

from app.core.authorization.models import (
    Delegation,
    RolePermissionScope,
    ScopeType,
    UserPermissionScope,
    UserRole,
)
from app.core.departments.models import Department
from app.core.organizations.models import Organization
from app.core.permissions.models import Permission
from app.core.roles.models import Role
from app.core.teams.models import Team, TeamMember
from app.core.users.models import User
from app.extensions import db

_counter = itertools.count()


def make_user(**overrides) -> User:
    n = next(_counter)
    defaults = dict(
        full_name=f"User {n}",
        email=f"user{n}@example.com",
        username=f"user{n}",
        password_hash="not-a-real-hash",
    )
    defaults.update(overrides)
    user = User(**defaults)
    db.session.add(user)
    db.session.flush()
    return user


def make_organization(**overrides) -> Organization:
    n = next(_counter)
    defaults = dict(name=f"Org {n}")
    defaults.update(overrides)
    org = Organization(**defaults)
    db.session.add(org)
    db.session.flush()
    return org


def make_department(organization: Organization, **overrides) -> Department:
    n = next(_counter)
    defaults = dict(name=f"Dept {n}", organization_id=organization.id)
    defaults.update(overrides)
    dept = Department(**defaults)
    db.session.add(dept)
    db.session.flush()
    return dept


def make_team(department: Department, **overrides) -> Team:
    n = next(_counter)
    defaults = dict(name=f"Team {n}", department_id=department.id)
    defaults.update(overrides)
    team = Team(**defaults)
    db.session.add(team)
    db.session.flush()
    return team


def add_team_member(team: Team, user: User) -> TeamMember:
    tm = TeamMember(team_id=team.id, user_id=user.id)
    db.session.add(tm)
    db.session.flush()
    return tm


def make_role(**overrides) -> Role:
    n = next(_counter)
    defaults = dict(name=f"role_{n}", display_name=f"Role {n}", is_active=True)
    defaults.update(overrides)
    role = Role(**defaults)
    db.session.add(role)
    db.session.flush()
    return role


def assign_role(user: User, role: Role, **overrides) -> UserRole:
    defaults = dict(user_id=user.id, role_id=role.id)
    defaults.update(overrides)
    ur = UserRole(**defaults)
    db.session.add(ur)
    db.session.flush()
    return ur


def make_permission(key: str, is_delegable: bool = False, **overrides) -> Permission:
    module, resource, action = key.split(".")
    defaults = dict(
        key=key, module=module, resource=resource, action=action, is_delegable=is_delegable
    )
    defaults.update(overrides)
    perm = Permission(**defaults)
    db.session.add(perm)
    db.session.flush()
    return perm


def grant_role_permission(
    role: Role,
    permission: Permission,
    scope_type: ScopeType,
    scope_id: int | None = None,
    is_active: bool = True,
    granted_by: User | None = None,
) -> RolePermissionScope:
    row = RolePermissionScope(
        role_id=role.id,
        permission_id=permission.id,
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=is_active,
        granted_by_user_id=granted_by.id if granted_by else None,
    )
    db.session.add(row)
    db.session.flush()
    return row


def grant_user_permission(
    user: User,
    permission: Permission,
    scope_type: ScopeType,
    scope_id: int | None = None,
    is_active: bool = True,
    granted_by: User | None = None,
) -> UserPermissionScope:
    row = UserPermissionScope(
        user_id=user.id,
        permission_id=permission.id,
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=is_active,
        granted_by_user_id=granted_by.id if granted_by else None,
    )
    db.session.add(row)
    db.session.flush()
    return row
