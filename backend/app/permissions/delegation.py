"""
User-targeted delegation eligibility and lifecycle -- AUTHORIZATION.md
§6 (eligibility), §9 (privilege-escalation rule set), §7 (department vs
team manager examples), DATABASE.md ("delegations" / revocation keeping
`user_permission_scopes.is_active` in sync).

Delegation eligibility -- five checks, all server-side, all must pass
(AUTHORIZATION.md §6), plus the explicit self-delegation guard (§9),
checked first and independent of the other five:

    0. Self-delegation is rejected outright, regardless of whether the
       other five checks would otherwise pass (§9).
    1. Possession -- the delegator holds the permission themselves (via
       role grant or user grant -- either counts).
    2. Delegable -- `permissions.is_delegable = TRUE` in the registry
       (the DB `Permission` row, which is the single source of truth
       for whether that permission can ever be delegated -- DATABASE.md
       "Privilege-escalation protection at the schema level").
    3. Scope containment -- the target scope is equal to or narrower
       than the delegator's own held scope for that permission.
    4. Target user's organizational relationship -- the delegatee
       actually belongs to (per `team_members`/`department_id`) the
       organizational unit the delegated scope refers to.
    5. Delegation authority itself -- the delegator holds
       `authz.grant.delegate` at a scope covering the target, checked
       through the same engine (not a bypass of it).

Checks 1 and 3 are both answered by a single `scope_covers` query against
the delegator's effective grants (`app/permissions/scope.py`) -- "holds
the permission at a scope equal to or broader than the target" is
exactly what containment means -- but they are still reported as
distinct failure reasons (`permission_not_held` vs `scope_escalation`)
so a caller can tell "you don't have this at all" apart from "you have
it, just not broadly enough."

"Does not cross organizational boundaries" (master context delegation
rule 6) is not a separate ad hoc check: because `scope_covers` only ever
returns True when the target scope is genuinely nested under the
delegator's held scope via the real hierarchy tables (never by tier
alone), a delegator whose held scope sits in one organization can never
have a grant whose scope_covers() call succeeds for a target in a
different organization. Check 3 alone makes cross-organization
delegation structurally impossible; see
tests/permissions/test_delegation.py::test_cross_organization_delegation_blocked.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.authorization.models import Delegation, ScopeType, UserPermissionScope
from app.core.departments.models import Department
from app.core.permissions.models import Permission
from app.core.teams.models import Team, TeamMember
from app.core.users.models import User
from app.extensions import db
from app.permissions.exceptions import DelegationDeniedError
from app.permissions.scope import scope_covers
from app.permissions.service import get_matching_grants, has_permission

DELEGATION_AUTHORITY_PERMISSION_KEY = "authz.grant.delegate"


@dataclass(frozen=True)
class DelegationCheckResult:
    allowed: bool
    reason_code: str | None
    message: str


def _target_user_in_scope(delegatee: User, scope_type: ScopeType, scope_id: int | None) -> bool:
    """
    AUTHORIZATION.md §6.4: the delegatee must actually belong to the
    organizational unit the delegated scope refers to, resolved via the
    real `team_members`/`department_id` relationships -- never via role
    names, department names, or `manager_user_id`.
    """
    if scope_type == ScopeType.GLOBAL:
        # No specific organizational unit to check membership against.
        return True
    if scope_type == ScopeType.SELF:
        # SELF carries no scope_id (DATABASE.md) -- nothing to check
        # structurally here; ownership is a resource-level question.
        return True
    if scope_type == ScopeType.ORGANIZATION:
        return delegatee.organization_id == scope_id
    if scope_type == ScopeType.DEPARTMENT:
        if delegatee.department_id == scope_id:
            return True
        member_of_team_in_department = (
            db.session.query(TeamMember)
            .join(Team, Team.id == TeamMember.team_id)
            .filter(TeamMember.user_id == delegatee.id, Team.department_id == scope_id)
            .first()
        )
        return member_of_team_in_department is not None
    if scope_type == ScopeType.TEAM:
        membership = (
            db.session.query(TeamMember)
            .filter(TeamMember.team_id == scope_id, TeamMember.user_id == delegatee.id)
            .first()
        )
        return membership is not None
    return False


def can_delegate(
    *,
    delegator: User,
    delegatee: User,
    permission_key: str,
    scope_type: ScopeType,
    scope_id: int | None,
) -> DelegationCheckResult:
    """Run every eligibility check for a proposed delegation, in order."""

    # Self-delegation: rejected outright, independent of the other five
    # checks (AUTHORIZATION.md §9).
    if delegator.id == delegatee.id:
        return DelegationCheckResult(
            allowed=False,
            reason_code="self_delegation",
            message="A user cannot delegate a permission to themselves.",
        )

    permission = db.session.query(Permission).filter_by(key=permission_key).one_or_none()
    if permission is None:
        return DelegationCheckResult(
            allowed=False,
            reason_code="permission_not_found",
            message=f"Permission '{permission_key}' does not exist.",
        )

    # 1. Possession -- delegator holds the permission at all (any scope,
    #    from either grant source).
    matching_grants = get_matching_grants(delegator, permission_key)
    if not matching_grants:
        return DelegationCheckResult(
            allowed=False,
            reason_code="permission_not_held",
            message=f"Delegator does not hold '{permission_key}'.",
        )

    # 3. Scope containment -- at least one held grant must cover the
    #    target scope. (Numbered to match AUTHORIZATION.md §6.3; checked
    #    here, before §6.2, purely because both draw on the same grant
    #    lookup above -- order does not change which checks must pass.)
    if not any(
        scope_covers(g.scope_type, g.scope_id, scope_type, scope_id) for g in matching_grants
    ):
        return DelegationCheckResult(
            allowed=False,
            reason_code="scope_escalation",
            message=(
                "Delegator's held scope does not cover the requested "
                "delegation scope."
            ),
        )

    # 2. Delegable -- permissions.is_delegable must be TRUE.
    if not permission.is_delegable:
        return DelegationCheckResult(
            allowed=False,
            reason_code="not_delegable",
            message=f"Permission '{permission_key}' is not delegable.",
        )

    # 4. Target user's organizational relationship.
    if not _target_user_in_scope(delegatee, scope_type, scope_id):
        return DelegationCheckResult(
            allowed=False,
            reason_code="target_outside_scope",
            message="Delegatee does not belong to the target organizational unit.",
        )

    # 5. Delegation authority itself -- checked through the same engine,
    #    not a bypass of it (AUTHORIZATION.md §6.5).
    if not has_permission(delegator, DELEGATION_AUTHORITY_PERMISSION_KEY, scope_type, scope_id):
        return DelegationCheckResult(
            allowed=False,
            reason_code="delegation_authority_missing",
            message=(
                f"Delegator does not hold '{DELEGATION_AUTHORITY_PERMISSION_KEY}' "
                "covering the target scope."
            ),
        )

    return DelegationCheckResult(
        allowed=True, reason_code=None, message="All delegation eligibility checks passed."
    )


def create_delegation(
    *,
    delegator: User,
    delegatee: User,
    permission_key: str,
    scope_type: ScopeType,
    scope_id: int | None,
) -> Delegation:
    """
    Run `can_delegate`; on success, atomically create the
    `UserPermissionScope` row and its linked `Delegation` lifecycle
    record. On failure, raise `DelegationDeniedError` and write nothing.
    """
    result = can_delegate(
        delegator=delegator,
        delegatee=delegatee,
        permission_key=permission_key,
        scope_type=scope_type,
        scope_id=scope_id,
    )
    if not result.allowed:
        raise DelegationDeniedError(result.reason_code, result.message)

    permission = db.session.query(Permission).filter_by(key=permission_key).one()

    user_permission_scope = UserPermissionScope(
        user_id=delegatee.id,
        permission_id=permission.id,
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=True,
        granted_by_user_id=delegator.id,
    )
    db.session.add(user_permission_scope)
    db.session.flush()  # assign PK before linking the Delegation row

    delegation = Delegation(
        delegator_user_id=delegator.id,
        delegatee_user_id=delegatee.id,
        resulting_user_permission_scope_id=user_permission_scope.id,
        delegated_at=datetime.now(timezone.utc),
    )
    db.session.add(delegation)
    db.session.commit()
    return delegation


def revoke_delegation(*, delegation: Delegation, revoked_by: User) -> Delegation:
    """
    Revoke a delegation: sets `revoked_at`/`revoked_by_user_id` on the
    `Delegation` row and `is_active = FALSE` on its linked
    `UserPermissionScope`, in one transaction -- "the grant and its audit
    trail stay linked and consistent by construction, not by convention"
    (AUTHORIZATION.md §6).
    """
    delegation.revoked_at = datetime.now(timezone.utc)
    delegation.revoked_by_user_id = revoked_by.id
    delegation.resulting_user_permission_scope.is_active = False
    db.session.commit()
    return delegation
