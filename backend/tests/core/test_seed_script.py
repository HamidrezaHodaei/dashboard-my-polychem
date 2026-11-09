"""
Idempotency test for scripts/seed_roles_permissions.py, per
IMPLEMENTATION_PLAN.md Phase 1 ("seed script idempotent").

Runs the seed functions directly against the pytest `app` fixture's
SQLite session (rather than shelling out to the script, which builds its
own app via create_app()) — running each step twice and asserting row
counts don't change the second time proves get_or_create() is doing its
job.
"""
from app.extensions import db
from app.core.roles.models import Role
from app.core.organizations.models import Organization
from app.core.departments.models import Department
from app.core.teams.models import Team
from app.core.permissions.models import Permission
from app.core.authorization.models import RolePermissionScope

from scripts.seed_roles_permissions import (
    SYSTEM_ROLES,
    ORGANIZATIONS,
    DEPARTMENTS,
    TEAMS,
    seed_roles,
    seed_organizations,
    seed_departments,
    seed_teams,
    seed_admin_global_grant,
    seed_registry_permissions_and_admin_grants,
)
from app.permissions.registry import REGISTRY


def _seed_everything():
    roles_by_name = seed_roles()
    orgs_by_name = seed_organizations()
    depts_by_name = seed_departments(orgs_by_name)
    seed_teams(depts_by_name)
    seed_admin_global_grant(roles_by_name)
    db.session.commit()


def test_seed_creates_expected_counts(app):
    _seed_everything()

    assert db.session.query(Role).count() == len(SYSTEM_ROLES)
    assert db.session.query(Organization).count() == len(ORGANIZATIONS)
    assert db.session.query(Department).count() == len(DEPARTMENTS)
    assert db.session.query(Team).count() == len(TEAMS)
    # Exactly one seed-time permission/grant, per IMPLEMENTATION_PLAN.md
    # Phase 1 ("no grants issued yet except admin @ GLOBAL").
    assert db.session.query(Permission).count() == 1
    assert db.session.query(RolePermissionScope).count() == 1


def test_seed_is_idempotent(app):
    _seed_everything()
    _seed_everything()  # run again — nothing should duplicate

    assert db.session.query(Role).count() == len(SYSTEM_ROLES)
    assert db.session.query(Organization).count() == len(ORGANIZATIONS)
    assert db.session.query(Department).count() == len(DEPARTMENTS)
    assert db.session.query(Team).count() == len(TEAMS)
    assert db.session.query(Permission).count() == 1
    assert db.session.query(RolePermissionScope).count() == 1


def test_seed_admin_role_has_global_grant(app):
    _seed_everything()

    admin_role = db.session.query(Role).filter_by(name="admin").one()
    grants = (
        db.session.query(RolePermissionScope)
        .filter_by(role_id=admin_role.id)
        .all()
    )
    assert len(grants) == 1
    assert grants[0].scope_type.value == "GLOBAL"
    assert grants[0].scope_id is None
    assert grants[0].granted_by_user_id is None


def test_seed_no_fake_users_created(app):
    from app.core.users.models import User

    _seed_everything()
    assert db.session.query(User).count() == 0


def test_seed_registry_permissions_grants_admin_every_core_and_authz_key(app):
    """Phase 4: the full REGISTRY (authz.grant.delegate + every
    core.<resource>.<action> key) must be seeded as DB rows and granted
    to admin @ GLOBAL, or the seeded admin role can never actually
    exercise any Phase 4 endpoint (has_permission only ever consults the
    DB Permission table, never the REGISTRY dict directly)."""
    roles_by_name = seed_roles()
    seed_registry_permissions_and_admin_grants(roles_by_name)
    db.session.commit()

    assert db.session.query(Permission).count() == len(REGISTRY)

    admin_role = roles_by_name["admin"]
    grants = db.session.query(RolePermissionScope).filter_by(role_id=admin_role.id).all()
    assert len(grants) == len(REGISTRY)
    assert all(g.scope_type.value == "GLOBAL" and g.scope_id is None for g in grants)

    # idempotent
    seed_registry_permissions_and_admin_grants(roles_by_name)
    db.session.commit()
    assert db.session.query(Permission).count() == len(REGISTRY)
    assert db.session.query(RolePermissionScope).filter_by(role_id=admin_role.id).count() == len(REGISTRY)
