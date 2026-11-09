"""
Service layer for /api/authz/delegations -- Phase 4's HTTP wrapper
around Phase 2's already-complete eligibility/lifecycle engine
(app/permissions/delegation.py). This module deliberately adds no new
authorization logic of its own -- `create_delegation` runs the full
five-check-plus-self-delegation eligibility gate before writing
anything, and `DelegationDeniedError` (raised on any failed check) is
already mapped to a 403 response in app/middleware/error_handlers.py.

Revocation authority (not itself part of the Phase 2 eligibility set,
since revocation is a distinct action from granting): a delegation may
be revoked by the original delegator, by the delegatee it was granted
to, or by anyone else who currently holds `authz.grant.delegate`
covering the delegation's own scope (an admin/broader-scoped override,
checked through the same engine rather than a bypass of it -- consistent
with how delegation authority itself is checked in
app/permissions/delegation.py).
"""
from app.core.authorization.models import Delegation, ScopeType
from app.core.users.models import User
from app.extensions import db
from app.permissions import delegation as delegation_engine
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import NotFoundError
from app.utils.pagination import paginate_query


def create_delegation(
    actor: User,
    *,
    delegatee_user_id: int,
    permission_key: str,
    scope_type: str,
    scope_id: int | None,
) -> Delegation:
    delegatee = db.session.get(User, delegatee_user_id)
    if delegatee is None or delegatee.deleted_at is not None:
        raise NotFoundError(f"User {delegatee_user_id} was not found.")

    try:
        resolved_scope_type = ScopeType(scope_type)
    except ValueError as exc:
        raise NotFoundError(f"'{scope_type}' is not a recognized scope type.") from exc

    return delegation_engine.create_delegation(
        delegator=actor,
        delegatee=delegatee,
        permission_key=permission_key,
        scope_type=resolved_scope_type,
        scope_id=scope_id,
    )


def _get_or_404(delegation_id: int) -> Delegation:
    delegation = db.session.get(Delegation, delegation_id)
    if delegation is None:
        raise NotFoundError(f"Delegation {delegation_id} was not found.")
    return delegation


def revoke_delegation(actor: User, delegation_id: int) -> Delegation:
    delegation = _get_or_404(delegation_id)
    if delegation.revoked_at is not None:
        return delegation  # already revoked; idempotent

    scope = delegation.resulting_user_permission_scope
    is_party = actor.id in (delegation.delegator_user_id, delegation.delegatee_user_id)
    has_override = has_permission(actor, "authz.grant.delegate", scope.scope_type, scope.scope_id)
    if not (is_party or has_override):
        raise PermissionDeniedError(
            "permission_denied",
            "Only the delegator, the delegatee, or a covering authz.grant.delegate holder may revoke this delegation.",
        )

    return delegation_engine.revoke_delegation(delegation=delegation, revoked_by=actor)


def list_my_delegations(actor: User, *, page: int, per_page: int):
    """Delegations where the actor is either the delegator or the
    delegatee -- no separate permission required beyond being a party to
    them, mirroring /api/me's self-scoped design in Phase 3."""
    query = (
        db.session.query(Delegation)
        .filter(
            db.or_(
                Delegation.delegator_user_id == actor.id,
                Delegation.delegatee_user_id == actor.id,
            )
        )
        .order_by(Delegation.id.desc())
    )
    return paginate_query(query, page, per_page)
