"""
Service layer for /api/core/organizations -- Phase 4 (IMPLEMENTATION_PLAN.md).

Permission checks live here, not in routes.py, so that CREATE (whose
target scope only exists once the request body is parsed) and LIST
(which needs to filter rows, not just allow/deny) can share the same
manual-check style as READ/UPDATE/DELETE (whose scope is resolved from
the loaded row) -- see the module docstring in
app/core/departments/services.py for the full rationale, identical here.

Permission key: core.organization.<action> (app/permissions/registry.py).
Scope rules:
    - create: parent_organization_id given -> (ORGANIZATION, parent_id);
      no parent -> (GLOBAL, None) -- creating a new top-level
      organization is a GLOBAL-only action.
    - read/update/delete (single row): (ORGANIZATION, organization.id) --
      an ORGANIZATION-scoped grant on an org covers that org itself
      (equal-scope match in scope_covers), as does any broader GLOBAL
      grant.
    - list: permission-only check, then row-level filtering by every
      ORGANIZATION-scoped grant the actor holds (GLOBAL grants see
      everything; DEPARTMENT/TEAM-scoped grants structurally cannot
      cover an ORGANIZATION target per scope_covers, so they contribute
      nothing here -- consistent with the engine, not a special case).
"""
from datetime import datetime, timezone

from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import ScopeType
from app.core.departments.models import Department
from app.core.organizations.models import Organization
from app.core.organizations.schemas import OrganizationCreate, OrganizationUpdate
from app.core.users.models import User
from app.extensions import db
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import get_matching_grants, has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "core"
ENTITY_TYPE = "organization"


def _require(actor: User, action: str, scope_type: ScopeType | None, scope_id: int | None) -> None:
    key = f"core.organization.{action}"
    if not has_permission(actor, key, scope_type, scope_id):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _get_or_404(organization_id: int) -> Organization:
    org = db.session.get(Organization, organization_id)
    if org is None or org.deleted_at is not None:
        raise NotFoundError(f"Organization {organization_id} was not found.")
    return org


def list_organizations(actor: User, *, page: int, per_page: int, include_inactive: bool = False):
    _require(actor, "read", None, None)

    query = db.session.query(Organization).filter(Organization.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(Organization.is_active.is_(True))

    grants = get_matching_grants(actor, "core.organization.read")
    if not any(g.scope_type == ScopeType.GLOBAL for g in grants):
        visible_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.ORGANIZATION}
        query = query.filter(Organization.id.in_(visible_ids)) if visible_ids else query.filter(db.false())

    query = query.order_by(Organization.id)
    return paginate_query(query, page, per_page)


def get_organization(actor: User, organization_id: int) -> Organization:
    org = _get_or_404(organization_id)
    _require(actor, "read", ScopeType.ORGANIZATION, org.id)
    return org


def create_organization(actor: User, payload: OrganizationCreate, *, ip_address: str | None) -> Organization:
    if payload.parent_organization_id is not None:
        parent = _get_or_404(payload.parent_organization_id)
        scope_type, scope_id = ScopeType.ORGANIZATION, parent.id
    else:
        scope_type, scope_id = ScopeType.GLOBAL, None
    _require(actor, "create", scope_type, scope_id)

    org = Organization(name=payload.name, parent_organization_id=payload.parent_organization_id)
    db.session.add(org)
    try:
        db.session.flush()
    except Exception as exc:  # IntegrityError etc.
        db.session.rollback()
        raise ConflictError("Could not create organization (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=org.id, metadata={"name": org.name}, ip_address=ip_address,
    )
    db.session.commit()
    return org


def update_organization(
    actor: User, organization_id: int, payload: OrganizationUpdate, *, ip_address: str | None
) -> Organization:
    org = _get_or_404(organization_id)
    _require(actor, "update", ScopeType.ORGANIZATION, org.id)

    changes = payload.model_dump(exclude_unset=True)
    if "parent_organization_id" in changes and changes["parent_organization_id"] is not None:
        if changes["parent_organization_id"] == org.id:
            raise ConflictError("An organization cannot be its own parent.")
        _get_or_404(changes["parent_organization_id"])

    for field, value in changes.items():
        setattr(org, field, value)

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update organization (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=org.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return org


def delete_organization(actor: User, organization_id: int, *, ip_address: str | None) -> None:
    org = _get_or_404(organization_id)
    _require(actor, "delete", ScopeType.ORGANIZATION, org.id)

    has_active_departments = (
        db.session.query(Department)
        .filter(Department.organization_id == org.id, Department.deleted_at.is_(None))
        .first()
    )
    if has_active_departments is not None:
        raise ConflictError(
            "Cannot delete an organization that still has active departments."
        )

    org.deleted_at = datetime.now(timezone.utc)
    org.is_active = False

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=org.id, ip_address=ip_address,
    )
    db.session.commit()
