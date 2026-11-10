"""
Navigation catalog + resolver for GET /api/me/navigation.

API.md: "permission-filtered menu tree". IMPLEMENTATION_PLAN.md Phase 3
originally deferred this ("navigation can return a static/minimal
structure until modules exist") -- Phase 4/4a now exist, so this
reflects the actual registered modules instead of a placeholder.

`_NAVIGATION_CATALOG` is a fixed, module-agnostic list -- not per-user
data. Nothing here is hardcoded PER USER: the same catalog is evaluated
for every caller, and `resolve_navigation()` filters it through the
existing effective-grants resolution (`app/permissions/service.py`),
exactly like any other authorization decision in this codebase.

Gating: a menu entry becomes visible if the user holds ANY permission
under that entry's `[module].[resource].*` (e.g. any of
tasks.task.create/read/update/delete/assign for the "tasks" entry), not
only its single displayed `permission` key -- a user who can only
`tasks.task.assign` (e.g. a team lead holding just a delegated assign
grant, AUTHORIZATION.md §7's Team Manager example) still needs to see
the Tasks section to do that job, even though they can't necessarily
list every task. `permission` in the response is kept as the entry's
canonical/representative key (used for display only); it is not
necessarily the specific permission that unlocked visibility for a
given user. The candidate set for each entry is derived from
`REGISTRY` itself (every key sharing that module+resource prefix) --
not a second hardcoded list -- so this stays in sync with the registry
automatically and needs no per-entry maintenance.
"""
from app.core.users.models import User
from app.permissions.registry import REGISTRY
from app.permissions.service import get_effective_grants


def _resource_prefix(permission: str) -> str:
    module, resource, _action = permission.split(".")
    return f"{module}.{resource}."


def _entry(key: str, label: str, path: str, permission: str) -> dict:
    if permission not in REGISTRY:
        raise KeyError(
            f"Navigation entry {key!r} references undefined permission {permission!r}"
        )
    prefix = _resource_prefix(permission)
    # export / print are not a reason to show a section on their own (they only matter next to `read`)
    gating_permissions = tuple(
        k for k in REGISTRY if k.startswith(prefix) and k.rsplit(".", 1)[-1] not in ("export", "print")
    )
    return {
        "key": key,
        "label": label,
        "path": path,
        "permission": permission,
        "_gating_permissions": gating_permissions,
    }


# English labels only -- no i18n/Persian-label decision is made here,
# since that is a frontend concern out of this (backend-only) task's
# scope; Nuxt can localize by `key` however it likes.
_NAVIGATION_CATALOG: list[dict] = [
    _entry("organizations", "Organizations", "/organizations", "core.organization.read"),
    _entry("departments", "Departments", "/departments", "core.department.read"),
    _entry("teams", "Teams", "/teams", "core.team.read"),
    _entry("users", "Users", "/users", "core.user.read"),
    _entry("roles", "Roles", "/roles", "core.role.read"),
    _entry("permissions", "Permissions", "/permissions", "core.permission.read"),
    # No distinct "view delegations" permission is documented anywhere
    # -- delegation authority itself (`authz.grant.delegate`) is the
    # only relevant permission key, so it gates this entry too, per
    # "do not invent permission keys".
    _entry("delegations", "Delegations", "/delegations", "authz.grant.delegate"),
    _entry("tasks", "Tasks", "/tasks", "tasks.task.read"),
    _entry("task_analytics", "Task Analytics", "/tasks/analytics", "tasks.analytics.read"),
    _entry("suppliers", "Suppliers", "/procurement/suppliers", "procurement.supplier.read"),
    _entry("customers", "Customers", "/crm/customers", "crm.customer.read"),
    _entry("crm_sales", "Sales", "/crm/sales", "crm.sale.read"),
    _entry("crm_dashboard", "Sales Dashboard", "/crm/dashboard", "crm.sale.read"),
    _entry("crm_settings", "CRM Settings", "/crm/settings", "crm.product.read"),
    _entry("logistics_companies", "Transport Companies", "/logistics/companies", "logistics.company.read"),
    _entry("logistics_drivers", "Drivers", "/logistics/drivers", "logistics.driver.read"),
]


def resolve_navigation(user: User) -> list[dict]:
    """
    Every catalog entry the user holds at least one of its gating
    permissions for, at ANY scope (step 1 of AUTHORIZATION.md §5's
    four-step check only -- menu visibility isn't tied to one specific
    resource the way an action is), in catalog order. Effective grants
    are resolved ONCE (not once per entry/permission) and reused as a
    plain key membership check -- same underlying data
    `has_permission()` uses, no duplicated/second RBAC logic.
    """
    held_permission_keys = {grant.permission_key for grant in get_effective_grants(user)}

    visible = []
    for entry in _NAVIGATION_CATALOG:
        if held_permission_keys.intersection(entry["_gating_permissions"]):
            visible.append(
                {
                    "key": entry["key"],
                    "label": entry["label"],
                    "path": entry["path"],
                    "permission": entry["permission"],
                }
            )
    return visible