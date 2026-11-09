"""
Phase 1 development seed script.

Creates, idempotently:
    - the 16 initial system roles (IMPLEMENTATION_PLAN.md Phase 1)
    - the initial organizational structure: دفتر مرکزی / کارخانه
      organizations; فروش, مالی, تدارکات, تولید, انبار, کنترل کیفیت,
      لجستیک departments; فروش داخلی team
    - exactly one seed-time grant: admin @ GLOBAL, per
      IMPLEMENTATION_PLAN.md Phase 1 ("no grants issued yet except
      admin @ GLOBAL")

Does NOT create:
    - any User row (no fake production users, no passwords — this script
      only creates roles/org structure/permission catalog rows)
    - the Phase 2 permission registry (app/permissions/registry.py) — the
      single permission row created here is an explicit, narrowly-scoped
      exception (see ADMIN_GLOBAL_PERMISSION_KEY below), not a preview of
      that registry

Idempotent: safe to run multiple times. Every entity is looked up by its
natural unique key before insert (get-or-create), and the whole run
commits once at the end.

Usage:
    python scripts/seed_roles_permissions.py
"""
import os
import sys

# Allow running as `python scripts/seed_roles_permissions.py` from the
# project root without needing to `pip install -e .` first.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.core.roles.models import Role
from app.core.organizations.models import Organization
from app.core.departments.models import Department
from app.core.teams.models import Team
from app.core.permissions.models import Permission
from app.core.authorization.models import RolePermissionScope, ScopeType
from app.permissions.registry import REGISTRY


# name (machine key) -> display_name (Persian, as given in IMPLEMENTATION_PLAN.md)
SYSTEM_ROLES: list[tuple[str, str]] = [
    ("admin", "Admin"),
    ("ceo", "مدیر عامل"),
    ("finance_manager", "مدیر مالی"),
    ("sales_manager", "مدیر فروش"),
    ("finance_specialist", "کارشناس مالی"),
    ("sales_specialist", "کارشناس فروش"),
    ("factory_manager", "مدیر کارخانه"),
    ("warehouse_keeper", "انبار دار"),
    ("warehouse_manager", "مدیر انبار"),
    ("chief_ledger_keeper", "سر دفتر دار"),
    ("quality_development_manager", "مدیر کیفی و توسعه"),
    ("technical_control", "کنترل فنی"),
    ("warehousing_officer", "مسئول انبار داری"),
    ("transport_officer", "مسئول حمل و نقل"),
    ("website_officer", "مسئول وب سایت"),
    ("procurement_manager", "مدیر تدارکات"),
]

# organization name -> parent organization name (None = top-level)
ORGANIZATIONS: list[tuple[str, str | None]] = [
    ("دفتر مرکزی", None),
    ("کارخانه", None),
]

# department name -> owning organization name
# DESIGN DECISION: IMPLEMENTATION_PLAN.md lists these seven departments and
# the two organizations, but does not specify which department sits under
# which organization. This mapping is a reasonable judgment call — head-
# office / commercial functions under دفتر مرکزی, factory-floor functions
# under کارخانه — and should be reviewed/corrected by whoever owns the
# real org chart before this is relied on beyond local development.
DEPARTMENTS: list[tuple[str, str]] = [
    ("فروش", "دفتر مرکزی"),
    ("مالی", "دفتر مرکزی"),
    ("تدارکات", "دفتر مرکزی"),
    ("لجستیک", "دفتر مرکزی"),
    ("تولید", "کارخانه"),
    ("انبار", "کارخانه"),
    ("کنترل کیفیت", "کارخانه"),
]

# team name -> owning department name
TEAMS: list[tuple[str, str]] = [
    ("فروش داخلی", "فروش"),
]

# DESIGN DECISION: the full permission registry is explicitly a Phase 2
# deliverable (IMPLEMENTATION_PLAN.md Phase 2, app/permissions/registry.py)
# and is NOT created here. IMPLEMENTATION_PLAN.md Phase 1 nonetheless says
# the seed script issues "no grants ... except admin @ GLOBAL" — satisfying
# that one line requires *a* permission row to attach the grant to, so
# exactly one narrowly-scoped, clearly-labeled placeholder permission is
# created for this purpose. It is not meant to anticipate or substitute
# for the Phase 2 registry's actual permission set, and should be revisited
# (likely replaced) once that registry exists.
ADMIN_GLOBAL_PERMISSION_KEY = "system.platform.manage"


def get_or_create(model, defaults=None, **lookup):
    instance = db.session.query(model).filter_by(**lookup).one_or_none()
    if instance is not None:
        return instance, False
    params = dict(lookup)
    params.update(defaults or {})
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()  # assign PK without committing yet
    return instance, True


def seed_roles() -> dict[str, Role]:
    roles_by_name = {}
    for name, display_name in SYSTEM_ROLES:
        role, created = get_or_create(
            Role,
            name=name,
            defaults={
                "display_name": display_name,
                "is_system_role": True,
                "is_active": True,
            },
        )
        roles_by_name[name] = role
        print(f"  {'created' if created else 'exists '} role       : {name} ({display_name})")
    return roles_by_name


def seed_organizations() -> dict[str, Organization]:
    orgs_by_name = {}
    for name, parent_name in ORGANIZATIONS:
        parent = orgs_by_name.get(parent_name) if parent_name else None
        org, created = get_or_create(
            Organization,
            name=name,
            defaults={
                "parent_organization_id": parent.id if parent else None,
                "is_active": True,
            },
        )
        orgs_by_name[name] = org
        print(f"  {'created' if created else 'exists '} organization: {name}")
    return orgs_by_name


def seed_departments(orgs_by_name: dict[str, Organization]) -> dict[str, Department]:
    depts_by_name = {}
    for name, org_name in DEPARTMENTS:
        organization = orgs_by_name[org_name]
        dept, created = get_or_create(
            Department,
            name=name,
            organization_id=organization.id,
            defaults={"is_active": True},
        )
        depts_by_name[name] = dept
        print(f"  {'created' if created else 'exists '} department  : {name} @ {org_name}")
    return depts_by_name


def seed_teams(depts_by_name: dict[str, Department]) -> dict[str, Team]:
    teams_by_name = {}
    for name, dept_name in TEAMS:
        department = depts_by_name[dept_name]
        team, created = get_or_create(
            Team,
            name=name,
            department_id=department.id,
            defaults={"is_active": True},
        )
        teams_by_name[name] = team
        print(f"  {'created' if created else 'exists '} team        : {name} @ {dept_name}")
    return teams_by_name


def seed_admin_global_grant(roles_by_name: dict[str, Role]) -> None:
    permission, perm_created = get_or_create(
        Permission,
        key=ADMIN_GLOBAL_PERMISSION_KEY,
        defaults={
            "module": "system",
            "resource": "platform",
            "action": "manage",
            "is_delegable": False,
            "description": (
                "Seed-time placeholder for the admin role's GLOBAL grant "
                "(IMPLEMENTATION_PLAN.md Phase 1). Not part of the Phase 2 "
                "permission registry — expect this to be revisited once "
                "app/permissions/registry.py exists."
            ),
        },
    )
    print(f"  {'created' if perm_created else 'exists '} permission  : {ADMIN_GLOBAL_PERMISSION_KEY}")

    admin_role = roles_by_name["admin"]
    grant, grant_created = get_or_create(
        RolePermissionScope,
        role_id=admin_role.id,
        permission_id=permission.id,
        scope_type=ScopeType.GLOBAL,
        defaults={
            "scope_id": None,
            "is_active": True,
            "granted_by_user_id": None,  # NULL for seed-time grants, per DATABASE.md
        },
    )
    print(f"  {'created' if grant_created else 'exists '} grant       : admin @ GLOBAL")


def seed_registry_permissions_and_admin_grants(roles_by_name: dict[str, Role]) -> None:
    """
    Phase 4: app/permissions/registry.py now holds the full documented
    permission set (authz.grant.delegate + every core.<resource>.<action>
    CRUD key). Every one of those needs a corresponding `permissions` row
    before `has_permission()` can ever match it -- the registry dict
    itself is never consulted at request time (app/permissions/service.py
    only ever queries the DB `Permission` table). This creates that row
    for each registry entry and grants it to `admin` @ GLOBAL, so the
    seeded admin role can actually exercise the Phase 4 endpoints instead
    of the placeholder-only grant below leaving it unable to call any of
    them.

    This does not replace `seed_admin_global_grant`'s
    `system.platform.manage` placeholder -- that grant is kept as-is
    (idempotent, harmless) since some business module may still reference
    it once Phase 4A/5 exist; this function only adds to it.
    """
    admin_role = roles_by_name["admin"]
    for key, definition in REGISTRY.items():
        permission, perm_created = get_or_create(
            Permission,
            key=key,
            defaults={
                "module": definition.module,
                "resource": definition.resource,
                "action": definition.action,
                "is_delegable": definition.is_delegable,
                "description": definition.description,
            },
        )
        print(f"  {'created' if perm_created else 'exists '} permission  : {key}")

        grant, grant_created = get_or_create(
            RolePermissionScope,
            role_id=admin_role.id,
            permission_id=permission.id,
            scope_type=ScopeType.GLOBAL,
            defaults={"scope_id": None, "is_active": True, "granted_by_user_id": None},
        )
        print(f"  {'created' if grant_created else 'exists '} grant       : admin @ GLOBAL -> {key}")


def seed_task_scoped_grants(
    roles_by_name: dict[str, Role],
    depts_by_name: dict[str, Department],
    teams_by_name: dict[str, Team],
) -> None:
    """
    IMPLEMENTATION_PLAN.md Phase 4a: "department- and team-scoped grants
    seeded for مدیر فروش and كارشناس فروش داخلی as a concrete test case."

    Permission sets and scopes are taken verbatim from AUTHORIZATION.md
    §7's own Department Manager / Team Manager worked examples (not
    invented here):
        مدیر فروش (sales_manager)   @ DEPARTMENT: فروش
            tasks.task.create, tasks.task.assign, tasks.task.read,
            tasks.analytics.read
        (team lead)                 @ TEAM: فروش داخلی
            tasks.task.create, tasks.task.assign, tasks.task.read

    SYSTEM_ROLES (the 16 seeded in Phase 1, unchanged here) has no role
    named exactly "كارشناس فروش داخلی" or a distinct team-lead role --
    only the generic "sales_specialist" (کارشناس فروش). Rather than
    inventing a 17th role, the team-scoped grant below is seeded onto
    that existing role, which is the closest documented match; this
    substitution should be revisited if/when a dedicated team-lead role
    is added to SYSTEM_ROLES.
    """
    department_manager_permission_keys = [
        "tasks.task.create", "tasks.task.assign", "tasks.task.read", "tasks.analytics.read",
    ]
    team_manager_permission_keys = ["tasks.task.create", "tasks.task.assign", "tasks.task.read"]

    sales_dept = depts_by_name["فروش"]
    sales_internal_team = teams_by_name["فروش داخلی"]

    def _grant(role_name: str, permission_keys: list[str], scope_type: ScopeType, scope_id: int):
        role = roles_by_name[role_name]
        for key in permission_keys:
            permission = db.session.query(Permission).filter_by(key=key).one_or_none()
            if permission is None:
                print(f"  SKIPPED     grant       : {role_name} -> {key} (permission row missing)")
                continue
            _grant_row, created = get_or_create(
                RolePermissionScope,
                role_id=role.id,
                permission_id=permission.id,
                scope_type=scope_type,
                scope_id=scope_id,
                defaults={"is_active": True, "granted_by_user_id": None},
            )
            print(
                f"  {'created' if created else 'exists '} grant       : "
                f"{role_name} @ {scope_type.value}:{scope_id} -> {key}"
            )

    _grant("sales_manager", department_manager_permission_keys, ScopeType.DEPARTMENT, sales_dept.id)
    _grant("sales_specialist", team_manager_permission_keys, ScopeType.TEAM, sales_internal_team.id)


def run() -> None:
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        print("Seeding system roles...")
        roles_by_name = seed_roles()

        print("Seeding organizational structure...")
        orgs_by_name = seed_organizations()
        depts_by_name = seed_departments(orgs_by_name)
        teams_by_name = seed_teams(depts_by_name)

        print("Seeding admin @ GLOBAL grant...")
        seed_admin_global_grant(roles_by_name)

        print("Seeding Phase 2/4 permission registry + admin @ GLOBAL grants...")
        seed_registry_permissions_and_admin_grants(roles_by_name)

        print("Seeding Phase 4a Tasks department/team-scoped grants...")
        seed_task_scoped_grants(roles_by_name, depts_by_name, teams_by_name)

        db.session.commit()
        print("Done.")


if __name__ == "__main__":
    run()
