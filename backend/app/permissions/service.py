"""
Effective grants resolution -- AUTHORIZATION.md §5, extended with
per-user DENY (single, system-wide merge rule -- every permission check
in the codebase goes through `get_effective_grants`, so this is the one
and only place the rule lives):

    Effective Grants(user) =
        (  Active Role Permission Grants  (all of the user's active roles,
                                           role_permission_scopes)
           UNION
           Active User ALLOW Grants       (user_permission_scopes, effect=ALLOW) )
        MINUS
           anything covered by an Active User DENY Grant
                                          (user_permission_scopes, effect=DENY)

Precedence, highest first:
    1. User DENY   -- always wins; removes every role/user grant of the
                      same permission key whose scope is covered by the
                      deny's scope (a GLOBAL deny removes the permission
                      completely -- this is what the per-user matrix writes).
    2. User ALLOW  -- direct grants (incl. delegations) on top of roles.
    3. Role grants -- UNION across ALL of the user's active roles
                      (multiple roles are additive; there is no
                      role-vs-role conflict because roles never deny).

So: "can the user do X?" == (some role OR a direct ALLOW grants X)
AND (no direct DENY removes X).

Both the role and user ALLOW sets are still drawn into one flat list
before any check runs -- "there is no precedence between them and no
special-casing" (§5) -- the only precedence added is that a DENY
subtracts from that list. This module only
implements steps 1-2 of the four-step check (Permission, Scope); step 3
(Resource Ownership / Organizational Relationship) is resource-specific
and is left to the caller (a future business module's service layer or
its `scope_resolver`), since no business module exists yet in Phase 2.
"""
from dataclasses import dataclass

from flask import has_request_context, request

from app.core.authorization.models import (
    PermissionEffect,
    ScopeType,
    UserRole,
    RolePermissionScope,
    UserPermissionScope,
)
from app.core.permissions.models import Permission
from app.core.roles.models import Role
from app.core.users.models import User
from app.extensions import db
from app.permissions.scope import scope_covers


@dataclass(frozen=True)
class Grant:
    """One resolved effective grant, flattened from either grant table."""

    permission_key: str
    scope_type: ScopeType
    scope_id: int | None
    source: str  # "role" or "user" -- for traceability/audit only, never
    #               used to give one source precedence over the other.


def get_effective_grants(user: User) -> list[Grant]:
    """Per-request memo for GET requests: a list screen asks "may this user update / review?" for
    every row, and each ask used to cost three queries. A GET never changes grants, so the answer
    is stable for the rest of that request. (Stored on the WSGI environ, which is per request.)"""
    cache = None
    if has_request_context() and request.method == "GET":
        cache = request.environ.setdefault("polychem.grants_cache", {})
        if user.id in cache:
            return list(cache[user.id])
    grants = _resolve_effective_grants(user)
    if cache is not None:
        cache[user.id] = tuple(grants)
    return grants


def _resolve_effective_grants(user: User) -> list[Grant]:
    """
    Resolve Effective Grants(user) per AUTHORIZATION.md §5: the union of
    active role_permission_scopes (via the user's active roles) and
    active user ALLOW grants, minus anything covered by an active user
    DENY grant -- as one flat list of grants (see module docstring).
    """
    grants: list[Grant] = []

    # Active Role Permission Grants, "via user's active roles" (§5) --
    # Role.is_active must be True for the role's grants to count.
    role_grant_rows = (
        db.session.query(RolePermissionScope, Permission)
        .join(Permission, RolePermissionScope.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermissionScope.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user.id,
            Role.is_active.is_(True),
            # Same visibility rule as permissions/matrix.py: a soft-deleted
            # role must stop granting, otherwise the matrix and the
            # enforced permissions disagree.
            Role.deleted_at.is_(None),
            RolePermissionScope.is_active.is_(True),
        )
        .all()
    )
    for scope_row, permission in role_grant_rows:
        grants.append(
            Grant(
                permission_key=permission.key,
                scope_type=scope_row.scope_type,
                scope_id=scope_row.scope_id,
                source="role",
            )
        )

    # Active User Permission Grants, directly on this user (ALLOW and DENY).
    user_grant_rows = (
        db.session.query(UserPermissionScope, Permission)
        .join(Permission, UserPermissionScope.permission_id == Permission.id)
        .filter(
            UserPermissionScope.user_id == user.id,
            UserPermissionScope.is_active.is_(True),
        )
        .all()
    )
    denies: list[Grant] = []
    for scope_row, permission in user_grant_rows:
        grant = Grant(
            permission_key=permission.key,
            scope_type=scope_row.scope_type,
            scope_id=scope_row.scope_id,
            source="user",
        )
        if scope_row.effect == PermissionEffect.DENY:
            denies.append(grant)
        else:
            grants.append(grant)

    if denies:
        grants = [
            g for g in grants
            if not any(
                d.permission_key == g.permission_key
                and scope_covers(d.scope_type, d.scope_id, g.scope_type, g.scope_id)
                for d in denies
            )
        ]

    return grants


def has_permission(
    user: User,
    permission_key: str,
    target_scope_type: ScopeType | None = None,
    target_scope_id: int | None = None,
) -> bool:
    """
    Steps 1-2 of AUTHORIZATION.md §5's four-step check:
        1. Permission Check -- does Effective Grants(user) contain this
           permission at all, from either source?
        2. Scope Check -- does at least one matching grant's scope cover
           the target (resolved from the resource itself)?

    If `target_scope_type` is None, only step 1 is evaluated (useful for
    "does this user hold this permission anywhere at all" checks). Step 3
    (resource ownership / organizational relationship) is NOT performed
    here -- it depends on the specific resource and is the caller's
    responsibility once a real resource exists (Phase 3/4+).
    """
    matching = [g for g in get_effective_grants(user) if g.permission_key == permission_key]
    if not matching:
        return False
    if target_scope_type is None:
        return True
    return any(
        scope_covers(g.scope_type, g.scope_id, target_scope_type, target_scope_id)
        for g in matching
    )


def get_matching_grants(user: User, permission_key: str) -> list[Grant]:
    """All effective grants of a given permission, regardless of scope."""
    return [g for g in get_effective_grants(user) if g.permission_key == permission_key]


def summarize_effective_permissions(user: User) -> list[dict]:
    """
    Groups `get_effective_grants(user)` by permission_key -- used by
    GET /api/me/permissions. Does not call any new RBAC logic: this is
    purely a reshaping of the same flat grant list every permission
    check in this codebase already goes through, so it can never drift
    from what `has_permission()` actually enforces.

    Delegated grants need no special handling here: DATABASE.md's
    `delegations` table only records the audit/lifecycle of a
    delegation -- the actual grant it produces is a normal
    `user_permission_scopes` row (a "resulting_user_permission_scope_id"
    row), which `get_effective_grants()` already includes with
    source="user" like any other direct user grant.

    Returns a list of {"key": ..., "scopes": [{"scope_type", "scope_id",
    "source"}, ...]}, one entry per distinct permission_key, in stable
    (first-seen) order.
    """
    grants = get_effective_grants(user)

    order: list[str] = []
    scopes_by_key: dict[str, list[Grant]] = {}
    for grant in grants:
        if grant.permission_key not in scopes_by_key:
            scopes_by_key[grant.permission_key] = []
            order.append(grant.permission_key)
        scopes_by_key[grant.permission_key].append(grant)

    return [
        {
            "key": key,
            "scopes": [
                {
                    "scope_type": g.scope_type.value,
                    "scope_id": g.scope_id,
                    "source": g.source,
                }
                for g in scopes_by_key[key]
            ],
        }
        for key in order
    ]


def is_admin(user: User) -> bool:
    """True when the user holds the seeded, active `admin` role."""
    return (
        db.session.query(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user.id,
            Role.name == "admin",
            Role.is_active.is_(True),
            Role.deleted_at.is_(None),
        )
        .first()
        is not None
    )
