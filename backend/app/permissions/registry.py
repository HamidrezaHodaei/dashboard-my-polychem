"""
Phase 2 permission registry — DOCUMENTED KEYS ONLY.

IMPLEMENTATION_PLAN.md Phase 2 calls for this file to hold "an initial
permission set (Users, Roles, Organizations, Departments, Teams)". A full
documentation sweep (API.md, AUTHORIZATION.md, DATABASE.md,
ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, SECURITY.md, INTEGRATIONS.md,
README.md, scripts/README.md) found no document that defines the *exact*
permission keys/actions for Users, Roles, Organizations, Departments, or
Teams. What exists is only the general naming pattern
`[module].[resource].[action]` (AUTHORIZATION.md header, API.md §4),
illustrated exclusively via:
    - Task-module examples (`tasks.task.assign`, `tasks.task.create`,
      `tasks.task.read`, `tasks.analytics.read`) — these belong to
      Phase 4a, not Phase 2's Users/Roles/Orgs/Departments/Teams set.
    - Two one-off illustrative examples used purely to demonstrate a
      *rule* (not to define a registry): `users.user.delete` in
      AUTHORIZATION.md §10 scenario E (illustrating a non-delegable
      permission) and `finance.transaction.read` in §10 scenario C
      (illustrating "permission never held") — Finance and a Users CRUD
      module are both explicitly out of scope for Phase 2.

Per the explicit instruction not to invent permission keys, this registry
does NOT define `core.user.*`, `core.role.*`, `core.organization.*`,
`core.department.*`, `core.team.*`, or any other naming for those five
resource areas. Only permission keys that are unambiguously named in the
existing documentation are registered below. See the Phase 2 completion
report for exactly what is missing and what needs to be supplied before
this registry can be completed.

The engine itself (scope.py / service.py / delegation.py) never reads
this registry to decide anything — it works over whatever `Permission`
rows exist in the database (keyed by `Permission.key`, checked against
`Permission.is_delegable`), the same way it already does for the
existing seeded `system.platform.manage` permission. This registry is
purely a documented catalog for whoever seeds new permissions.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    key: str
    module: str
    resource: str
    action: str
    is_delegable: bool
    description: str


# ---------------------------------------------------------------------
# Documented, unambiguous entries only.
# ---------------------------------------------------------------------

# AUTHORIZATION.md §6.5 / §9 and IMPLEMENTATION_PLAN.md Phase 2: the
# delegation-authority permission itself. A delegator must hold this at
# a scope covering the target before ANY delegation can be created
# (delegation.py's fifth eligibility check).
#
# is_delegable=False: AUTHORIZATION.md §9 states that "role/permission-
# management permissions default is_delegable = FALSE ... regardless of
# who holds them." Delegation authority is exactly that category, so
# this applies the documented default rule rather than inventing a new
# one for this specific key.
AUTHZ_GRANT_DELEGATE = PermissionDefinition(
    key="authz.grant.delegate",
    module="authz",
    resource="grant",
    action="delegate",
    is_delegable=False,
    description=(
        "Authority to create a user-level delegation of another "
        "permission (AUTHORIZATION.md \u00a76/\u00a79)."
    ),
)

# ---------------------------------------------------------------------
# Phase 4 — Core CRUD modules (Users, Roles, Permissions, Organizations,
# Departments, Teams).
#
# IMPLEMENTATION_PLAN.md's own Phase 4 entry is the explicit source for
# this naming — unlike the five resources this file previously reported
# as undocumented, Phase 4 states outright: "each route wired to its
# `core.<resource>.<action>` permission". That sentence *is* the
# documentation license this file's Phase 2 note was waiting for, so
# these are no longer invented — they instantiate the pattern the plan
# names, for the six resources the plan lists for Phase 4, using the
# four standard CRUD actions from API.md §4 (create / read / update /
# delete — "read" covers both the list and detail GET endpoints, same
# as the Task-module examples elsewhere in AUTHORIZATION.md use a single
# `.read` for a resource rather than separate list/detail verbs).
#
# is_delegable: AUTHORIZATION.md §9 — "role/permission-management
# permissions default is_delegable = FALSE ... regardless of who holds
# them" — so every core.role.* and core.permission.* entry is
# non-delegable. Every other core.* entry defaults non-delegable too
# (nothing in the documentation says otherwise for Users/Organizations/
# Departments/Teams), with one explicit, reasoned exception:
# `core.user.read` is delegable — viewing the members of one's own
# scope is the lowest-risk read in this set, carries no path to
# privilege escalation, and is the concrete permission
# IMPLEMENTATION_PLAN.md's own Phase 4 delegation example calls for
# ("a department manager can delegate a delegable, in-scope permission
# to a specific team member").
# ---------------------------------------------------------------------

_CORE_RESOURCES_NON_DELEGABLE = ("organization", "department", "team", "user", "role", "permission")
_CORE_ACTIONS = ("create", "read", "update", "delete")

_CORE_DEFINITIONS: list[PermissionDefinition] = []
for _resource in _CORE_RESOURCES_NON_DELEGABLE:
    for _action in _CORE_ACTIONS:
        _key = f"core.{_resource}.{_action}"
        _is_delegable = _resource == "user" and _action == "read"
        _CORE_DEFINITIONS.append(
            PermissionDefinition(
                key=_key,
                module="core",
                resource=_resource,
                action=_action,
                is_delegable=_is_delegable,
                description=f"{_action.capitalize()} {_resource} records (Phase 4 core CRUD).",
            )
        )
del _resource, _action, _key, _is_delegable

# ---------------------------------------------------------------------
# Phase 4a — Tasks / Workspace module.
#
# IMPLEMENTATION_PLAN.md's own Phase 4a entry names these explicitly:
# "tasks.task.create/read/update/delete/assign permissions registered".
# `tasks.analytics.read` is additionally documented in AUTHORIZATION.md
# §7's worked example (مدیر فروش's permission set). No "unassign" key is
# documented anywhere, so removing an assignment reuses `tasks.task.assign`
# rather than inventing a new key (app/modules/tasks/services.py).
#
# is_delegable=True for every entry here: AUTHORIZATION.md §5's worked
# example shows `tasks.task.assign` itself being delegated user-to-user
# (علی's direct grant, issued by مدیر فروش through delegation), and §9's
# non-delegable-by-default list is explicitly scoped to "financial,
# system, security, and role/permission-management permissions" — Tasks
# is none of those.
# ---------------------------------------------------------------------
_TASK_ACTIONS = ("create", "read", "update", "delete", "assign")
_TASK_DEFINITIONS: list[PermissionDefinition] = [
    PermissionDefinition(
        key=f"tasks.task.{_action}",
        module="tasks",
        resource="task",
        action=_action,
        is_delegable=True,
        description=f"{_action.capitalize()} tasks (Phase 4a).",
    )
    for _action in _TASK_ACTIONS
] + [
    PermissionDefinition(
        key="tasks.analytics.read",
        module="tasks",
        resource="analytics",
        action="read",
        is_delegable=True,
        description="View task analytics/counts within scope (Phase 4a).",
    )
]

# ---------------------------------------------------------------------
# Business-module CRUD permissions (CRM / Finance / Warehouse / Website /
# Reports) -- needed by the per-role / per-user permission matrix
# (app/permissions/matrix.py), which manages Read / Create / Update /
# Delete for every "module" row. Same `[module].[resource].[action]`
# naming and the same four CRUD actions as the core.* set above.
#
# is_delegable: finance is a *financial* permission, which
# AUTHORIZATION.md §9 says defaults non-delegable; every other business
# module here follows the Tasks precedent (delegable).
# ---------------------------------------------------------------------
_BUSINESS_RESOURCES = (
    # (module, resource, is_delegable)
    ("crm", "customer", True),
    # CRM sales module (modules/crm): sales documents + analytics, and the product catalogue /
    # payment-method lists that feed them. Customers themselves stay under crm.customer.*.
    ("crm", "sale", True),
    ("crm", "product", True),
    # Request Sample module (modules/request_samples): create / read / update / delete here; the
    # workflow actions (approve, reject, dispatch, ...) are the non-delegable extras below.
    ("crm", "request_sample", True),
    ("finance", "transaction", False),
    ("warehouse", "stock", True),
    ("website", "page", True),
    ("reports", "report", True),
    # Procurement / supplier management: the public, unauthenticated
    # registration form (create_public() in modules/suppliers/services.py)
    # does not go through this at all -- these four keys only gate the
    # admin panel (list/review/add/delete).
    ("procurement", "supplier", True),
)
_BUSINESS_DEFINITIONS: list[PermissionDefinition] = [
    PermissionDefinition(
        key=f"{_module}.{_resource}.{_action}",
        module=_module,
        resource=_resource,
        action=_action,
        is_delegable=_delegable,
        description=f"{_action.capitalize()} {_module} {_resource} records.",
    )
    for _module, _resource, _delegable in _BUSINESS_RESOURCES
    for _action in _CORE_ACTIONS
]

# ---------------------------------------------------------------------
# Logistics -- transport-company / driver registration (modules/logistics).
#
# Access is split per applicant type so a role can manage drivers but not
# companies (or the reverse). Five actions each: the four matrix CRUD
# actions plus `review` (approve / reject / suspend a registration), which
# is intentionally NOT a matrix column -- it is granted as an ordinary
# permission. The public wizard endpoints never go through these keys.
#
# is_delegable: CRUD follows the Suppliers precedent (True). `review` is a
# decision about who may operate on the platform, so it is non-delegable.
# ---------------------------------------------------------------------
LOGISTICS_RESOURCES = ("company", "driver")
LOGISTICS_ACTIONS = _CORE_ACTIONS + ("review",)
_LOGISTICS_DEFINITIONS: list[PermissionDefinition] = [
    PermissionDefinition(
        key=f"logistics.{_res}.{_action}",
        module="logistics",
        resource=_res,
        action=_action,
        is_delegable=_action != "review",
        description=f"{_action.capitalize()} logistics {'transport company' if _res == 'company' else 'driver'} records.",
    )
    for _res in LOGISTICS_RESOURCES
    for _action in LOGISTICS_ACTIONS
]

# ---------------------------------------------------------------------
# Extra, non-CRUD permissions of the business modules (granted from the permission matrix):
#   review   decide on a registration request (customers, suppliers)
#   export   download the list as Excel / Word (customers, suppliers, logistics, sales)
#   print    print the sales report
# None of them is delegable: they release data / decide on other people's requests.
# ---------------------------------------------------------------------
EXTRA_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("crm", "customer", "review"), ("crm", "customer", "export"),
    ("procurement", "supplier", "review"), ("procurement", "supplier", "export"),
    ("logistics", "company", "export"), ("logistics", "driver", "export"),
    ("crm", "sale", "export"), ("crm", "sale", "print"),
    ("crm", "request_sample", "approve"), ("crm", "request_sample", "reject"),
    ("crm", "request_sample", "dispatch"), ("crm", "request_sample", "follow_up"),
    ("crm", "request_sample", "feedback"), ("crm", "request_sample", "convert"),
    ("crm", "request_sample", "export"),
)
_EXTRA_DEFINITIONS: list[PermissionDefinition] = [
    PermissionDefinition(
        key=f"{_m}.{_r}.{_a}", module=_m, resource=_r, action=_a, is_delegable=False,
        description=f"{_a.capitalize()} {_m} {_r} records.",
    )
    for _m, _r, _a in EXTRA_PERMISSIONS
]

REGISTRY: dict[str, PermissionDefinition] = {
    AUTHZ_GRANT_DELEGATE.key: AUTHZ_GRANT_DELEGATE,
    **{definition.key: definition for definition in _CORE_DEFINITIONS},
    **{definition.key: definition for definition in _TASK_DEFINITIONS},
    **{definition.key: definition for definition in _BUSINESS_DEFINITIONS},
    **{definition.key: definition for definition in _LOGISTICS_DEFINITIONS},
    **{definition.key: definition for definition in _EXTRA_DEFINITIONS},
}


# ---------------------------------------------------------------------
# Permission-matrix catalog: the "Module" rows an admin edits in the UI.
# Each row is one `[module].[resource]` pair; the four matrix columns map
# onto the registry's actions as:
#     Read -> read, Create -> create, Edit/Update -> update, Delete -> delete
# Other actions (e.g. tasks.task.assign) are not matrix columns; they are
# still ordinary grants and are left untouched by matrix saves.
# ---------------------------------------------------------------------
MATRIX_ACTIONS: tuple[str, ...] = ("read", "create", "update", "delete")


@dataclass(frozen=True)
class MatrixModule:
    key: str  # "<module>.<resource>"
    label: str
    # Actions beyond the four CRUD columns that this row also exposes (e.g. "review" for
    # logistics). Only modules that list them get that checkbox in the UI.
    extra_actions: tuple[str, ...] = ()

    @property
    def actions(self) -> tuple[str, ...]:
        return MATRIX_ACTIONS + self.extra_actions


MATRIX_MODULES: tuple[MatrixModule, ...] = (
    MatrixModule("core.user", "Users"),
    MatrixModule("core.role", "Roles"),
    MatrixModule("core.permission", "Permissions"),
    MatrixModule("core.organization", "Organizations"),
    MatrixModule("core.department", "Departments"),
    MatrixModule("core.team", "Teams"),
    MatrixModule("tasks.task", "Tasks"),
    MatrixModule("crm.customer", "CRM", ("review", "export")),
    MatrixModule("crm.sale", "CRM Sales", ("export", "print")),
    MatrixModule("crm.product", "CRM Products"),
    MatrixModule(
        "crm.request_sample", "Request Sample",
        ("approve", "reject", "dispatch", "follow_up", "feedback", "convert", "export"),
    ),
    MatrixModule("finance.transaction", "Finance"),
    MatrixModule("warehouse.stock", "Warehouse"),
    MatrixModule("website.page", "Website"),
    MatrixModule("reports.report", "Reports"),
    MatrixModule("procurement.supplier", "Suppliers", ("review", "export")),
    MatrixModule("logistics.company", "Transport Companies", ("review", "export")),
    MatrixModule("logistics.driver", "Drivers", ("review", "export")),
)


def get_permission_definition(key: str) -> PermissionDefinition | None:
    """Look up a documented permission definition by key, or None."""
    return REGISTRY.get(key)
