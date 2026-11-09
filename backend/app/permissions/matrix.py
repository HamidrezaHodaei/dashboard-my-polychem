"""
Permission matrix (Module x Read/Create/Edit/Delete) for roles and users.

This is a *view + bulk-edit layer* over the existing grant tables -- it
adds no second authorization mechanism. Everything it writes is an
ordinary `role_permission_scopes` / `user_permission_scopes` row that
`app/permissions/service.py::get_effective_grants` already resolves, so
what the admin ticks in the UI is exactly what every backend permission
check enforces.

Columns -> permission actions:  Read=read, Create=create,
Edit/Update=update, Delete=delete  (registry.MATRIX_ACTIONS), plus any
`extra_actions` a row declares (logistics rows add `review`).
Rows -> `[module].[resource]` pairs (registry.MATRIX_MODULES).

ROLE matrix
    checked   == the role has at least one active grant of that
                 permission (any scope; `scoped` flags non-GLOBAL-only).
    save      == checked -> ensure an active GLOBAL grant exists (leave an
                 existing scoped grant alone); unchecked -> deactivate
                 every active grant of that permission on the role.

USER matrix (cell value = the user's FINAL effective access)
    save, desired=True : lift the user's DENY rows for that permission; if
                         neither a role nor a direct ALLOW grants it, add a
                         direct GLOBAL ALLOW.
    save, desired=False: if the user currently has it (via a role or a
                         direct ALLOW), add a direct GLOBAL DENY. DENY
                         always wins in the merge (see service.py).
    Untouched cells (desired == current) write nothing, so saving the
    matrix never rewrites delegation rows.
"""
from app.core.authorization.models import (
    PermissionEffect,
    RolePermissionScope,
    ScopeType,
    UserPermissionScope,
    UserRole,
)
from app.core.permissions.models import Permission
from app.core.roles.models import Role
from app.core.users.models import User
from app.extensions import db
from app.permissions.registry import (
    MATRIX_MODULES,
    REGISTRY,
)
from app.permissions.service import get_effective_grants
from app.utils.exceptions import NotFoundError

PRECEDENCE_RULES = [
    "1. A direct per-user DENY always wins and removes the permission.",
    "2. A direct per-user ALLOW (including delegations) adds to the user's roles.",
    "3. Role permissions are merged (union) across ALL of the user's active roles.",
    "Final access = (any role OR direct ALLOW) AND NOT direct DENY.",
]


def matrix_catalog() -> list[dict]:
    return [
        {
            "key": module.key,
            "label": module.label,
            "actions": list(module.actions),
        }
        for module in MATRIX_MODULES
    ]


def _all_matrix_keys() -> list[str]:
    return [f"{m.key}.{action}" for m in MATRIX_MODULES for action in m.actions]


def ensure_registry_permissions() -> dict[str, Permission]:
    """
    Make sure a `permissions` row exists for every matrix key (the
    registry dict is documentation only -- has_permission() reads the
    table). Flushes but never commits; returns {key: Permission}.
    """
    keys = _all_matrix_keys()
    rows = {p.key: p for p in db.session.query(Permission).filter(Permission.key.in_(keys)).all()}
    for key in keys:
        if key in rows:
            continue
        definition = REGISTRY[key]
        permission = Permission(
            key=key, module=definition.module, resource=definition.resource,
            action=definition.action, is_delegable=definition.is_delegable,
            description=definition.description,
        )
        db.session.add(permission)
        rows[key] = permission
    db.session.flush()
    return rows


def validate_cells(cells: dict) -> list[tuple[str, str, bool]]:
    """-> [(module_key, action, desired)] or raises ValueError."""
    valid_modules = {m.key: m for m in MATRIX_MODULES}
    out: list[tuple[str, str, bool]] = []
    for module_key, actions in (cells or {}).items():
        if module_key not in valid_modules:
            raise ValueError(f"Unknown module '{module_key}'.")
        for action, desired in (actions or {}).items():
            if action not in valid_modules[module_key].actions:
                raise ValueError(f"Unknown action '{action}' for module '{module_key}'.")
            if not isinstance(desired, bool):
                raise ValueError(f"Cell {module_key}.{action} must be true or false.")
            out.append((module_key, action, desired))
    return out


# ---------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------
def _active_role_grants(role_id: int) -> dict[str, list[RolePermissionScope]]:
    rows = (
        db.session.query(RolePermissionScope, Permission)
        .join(Permission, Permission.id == RolePermissionScope.permission_id)
        .filter(RolePermissionScope.role_id == role_id, RolePermissionScope.is_active.is_(True))
        .all()
    )
    by_key: dict[str, list[RolePermissionScope]] = {}
    for scope_row, permission in rows:
        by_key.setdefault(permission.key, []).append(scope_row)
    return by_key


def get_role_matrix(role: Role) -> dict:
    grants = _active_role_grants(role.id)
    cells: dict[str, dict] = {}
    for module in MATRIX_MODULES:
        cells[module.key] = {}
        for action in module.actions:
            rows = grants.get(f"{module.key}.{action}", [])
            cells[module.key][action] = {
                "granted": bool(rows),
                "scoped": bool(rows) and not any(r.scope_type == ScopeType.GLOBAL for r in rows),
            }
    return {"modules": matrix_catalog(), "cells": cells}


def apply_role_matrix(role: Role, cells: dict, actor: User) -> list[dict]:
    """Returns the list of changes made (for the audit log). Caller commits."""
    desired_cells = validate_cells(cells)
    permissions = ensure_registry_permissions()
    grants = _active_role_grants(role.id)
    changes: list[dict] = []

    for module_key, action, desired in desired_cells:
        key = f"{module_key}.{action}"
        permission = permissions[key]
        active = grants.get(key, [])
        if desired and not active:
            existing = (
                db.session.query(RolePermissionScope)
                .filter_by(role_id=role.id, permission_id=permission.id, scope_type=ScopeType.GLOBAL)
                .first()
            )
            if existing is not None:
                existing.is_active = True
                existing.granted_by_user_id = actor.id
            else:
                db.session.add(RolePermissionScope(
                    role_id=role.id, permission_id=permission.id, scope_type=ScopeType.GLOBAL,
                    scope_id=None, is_active=True, granted_by_user_id=actor.id,
                ))
            changes.append({"permission": key, "change": "granted"})
        elif not desired and active:
            for row in active:
                row.is_active = False
            changes.append({"permission": key, "change": "revoked"})

    db.session.flush()
    return changes


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------
def _active_user_roles(user_id: int) -> list[tuple[UserRole, Role]]:
    return (
        db.session.query(UserRole, Role)
        .join(Role, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user_id, Role.is_active.is_(True), Role.deleted_at.is_(None))
        .all()
    )


def _role_grants_for_user(user_id: int) -> dict[str, set[str]]:
    """permission key -> set of role display names granting it (active roles only)."""
    rows = (
        db.session.query(Permission.key, Role.display_name)
        .join(RolePermissionScope, RolePermissionScope.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermissionScope.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user_id,
            Role.is_active.is_(True),
            Role.deleted_at.is_(None),
            RolePermissionScope.is_active.is_(True),
        )
        .all()
    )
    out: dict[str, set[str]] = {}
    for key, role_name in rows:
        out.setdefault(key, set()).add(role_name)
    return out


def _direct_rows_for_user(user_id: int) -> dict[str, list[UserPermissionScope]]:
    rows = (
        db.session.query(UserPermissionScope, Permission)
        .join(Permission, Permission.id == UserPermissionScope.permission_id)
        .filter(UserPermissionScope.user_id == user_id, UserPermissionScope.is_active.is_(True))
        .all()
    )
    out: dict[str, list[UserPermissionScope]] = {}
    for scope_row, permission in rows:
        out.setdefault(permission.key, []).append(scope_row)
    return out


def get_user_matrix(user: User) -> dict:
    role_grants = _role_grants_for_user(user.id)
    direct = _direct_rows_for_user(user.id)
    effective_keys = {g.permission_key for g in get_effective_grants(user)}

    cells: dict[str, dict] = {}
    for module in MATRIX_MODULES:
        cells[module.key] = {}
        for action in module.actions:
            key = f"{module.key}.{action}"
            rows = direct.get(key, [])
            has_deny = any(r.effect == PermissionEffect.DENY for r in rows)
            has_allow = any(r.effect == PermissionEffect.ALLOW for r in rows)
            cells[module.key][action] = {
                "effective": key in effective_keys,
                "from_role": key in role_grants,
                "role_names": sorted(role_grants.get(key, [])),
                "direct": "DENY" if has_deny else ("ALLOW" if has_allow else None),
            }
    return {"modules": matrix_catalog(), "cells": cells, "precedence": PRECEDENCE_RULES}


def apply_user_matrix(user: User, cells: dict, actor: User) -> list[dict]:
    """
    Returns the changes made. Caller commits. Raises PermissionError-like
    ValueError for malformed cells; escalation checks (actor must hold the
    permission it is allowing) are done by the caller via `actor_can_grant`.
    """
    desired_cells = validate_cells(cells)
    permissions = ensure_registry_permissions()
    role_grants = _role_grants_for_user(user.id)
    direct = _direct_rows_for_user(user.id)
    effective_keys = {g.permission_key for g in get_effective_grants(user)}
    changes: list[dict] = []

    for module_key, action, desired in desired_cells:
        key = f"{module_key}.{action}"
        permission = permissions[key]
        rows = direct.get(key, [])
        denies = [r for r in rows if r.effect == PermissionEffect.DENY]
        allows = [r for r in rows if r.effect == PermissionEffect.ALLOW]

        if desired:
            for row in denies:
                row.is_active = False
            if denies:
                changes.append({"permission": key, "change": "deny_removed"})
            if key not in role_grants and not allows:
                db.session.add(UserPermissionScope(
                    user_id=user.id, permission_id=permission.id, scope_type=ScopeType.GLOBAL,
                    scope_id=None, effect=PermissionEffect.ALLOW, is_active=True,
                    granted_by_user_id=actor.id,
                ))
                changes.append({"permission": key, "change": "allowed"})
        else:
            if key in effective_keys and not denies:
                db.session.add(UserPermissionScope(
                    user_id=user.id, permission_id=permission.id, scope_type=ScopeType.GLOBAL,
                    scope_id=None, effect=PermissionEffect.DENY, is_active=True,
                    granted_by_user_id=actor.id,
                ))
                changes.append({"permission": key, "change": "denied"})

    db.session.flush()
    return changes


def desired_true_keys(cells: dict) -> list[str]:
    return [f"{m}.{a}" for m, a, d in validate_cells(cells) if d]


def get_user_access_summary(user: User) -> dict:
    """Roles, role-sourced grants, direct grants, and the merged effective result."""
    roles = [
        {
            "id": role.id, "name": role.name, "display_name": role.display_name,
            "organization_id": ur.organization_id,
        }
        for ur, role in _active_user_roles(user.id)
    ]

    role_rows = (
        db.session.query(RolePermissionScope, Permission, Role)
        .join(Permission, Permission.id == RolePermissionScope.permission_id)
        .join(UserRole, UserRole.role_id == RolePermissionScope.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user.id, Role.is_active.is_(True),
            Role.deleted_at.is_(None), RolePermissionScope.is_active.is_(True),
        )
        .order_by(Permission.key)
        .all()
    )
    role_grants = [
        {
            "permission_key": p.key, "scope_type": g.scope_type.value, "scope_id": g.scope_id,
            "role_id": r.id, "role_name": r.display_name,
        }
        for g, p, r in role_rows
    ]

    direct_rows = (
        db.session.query(UserPermissionScope, Permission)
        .join(Permission, Permission.id == UserPermissionScope.permission_id)
        .filter(UserPermissionScope.user_id == user.id, UserPermissionScope.is_active.is_(True))
        .order_by(Permission.key)
        .all()
    )
    direct_grants = [
        {
            "id": g.id, "permission_key": p.key, "scope_type": g.scope_type.value,
            "scope_id": g.scope_id, "effect": g.effect.value,
        }
        for g, p in direct_rows
    ]

    effective: dict[str, list[dict]] = {}
    for grant in get_effective_grants(user):
        effective.setdefault(grant.permission_key, []).append(
            {"scope_type": grant.scope_type.value, "scope_id": grant.scope_id, "source": grant.source}
        )

    return {
        "roles": roles,
        "role_grants": role_grants,
        "direct_grants": direct_grants,
        "effective": [{"key": k, "scopes": v} for k, v in sorted(effective.items())],
        "precedence": PRECEDENCE_RULES,
    }
