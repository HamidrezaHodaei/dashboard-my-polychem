"""
Scope containment/expansion — AUTHORIZATION.md's scope taxonomy:

    GLOBAL > ORGANIZATION > DEPARTMENT > TEAM > SELF

"A broader scope may cover a narrower scope" (master context /
AUTHORIZATION.md §1). Containment for ORGANIZATION/DEPARTMENT/TEAM is
resolved via the *actual* organizational hierarchy tables
(organizations / departments / teams / team_members) — never inferred
from `manager_user_id`, role names, department names, or any
frontend-supplied state. This module only ever reads
Organization.departments / Department.teams / Department.organization_id
/ Team.department_id, which are the real FKs verified in Phase 1.

SELF has no `scope_id` (DATABASE.md: "NULL when GLOBAL/SELF") — it is
not a hierarchy node to look up. Whether a SELF-scoped grant actually
covers a given resource is a resource-ownership question, answered by
step 3 of the four-step check (AUTHORIZATION.md §5), not by this module.
Here, SELF only participates in *ranking* (it is the narrowest tier), so
a broader scope such as DEPARTMENT is considered to structurally cover a
SELF-scoped target -- the concrete ownership check still has to happen
separately wherever the resource is available (Phase 3/4+).
"""
from app.core.authorization.models import ScopeType
from app.core.departments.models import Department
from app.core.teams.models import Team
from app.extensions import db

# Ranking used only to decide whether one scope's *tier* is broader than,
# equal to, or narrower than another's. Hierarchical containment for
# non-equal, non-GLOBAL cases is always additionally verified against the
# real FK relationships below -- rank alone never authorizes anything.
_SCOPE_RANK = {
    ScopeType.GLOBAL: 4,
    ScopeType.ORGANIZATION: 3,
    ScopeType.DEPARTMENT: 2,
    ScopeType.TEAM: 1,
    ScopeType.SELF: 0,
}


def _department_organization_id(department_id: int) -> int | None:
    department = db.session.get(Department, department_id)
    return department.organization_id if department is not None else None


def _team_department_id(team_id: int) -> int | None:
    team = db.session.get(Team, team_id)
    return team.department_id if team is not None else None


def _team_organization_id(team_id: int) -> int | None:
    team = db.session.get(Team, team_id)
    if team is None:
        return None
    department = db.session.get(Department, team.department_id)
    return department.organization_id if department is not None else None


def scope_covers(
    grant_scope_type: ScopeType,
    grant_scope_id: int | None,
    target_scope_type: ScopeType,
    target_scope_id: int | None,
) -> bool:
    """
    Does a grant held at (grant_scope_type, grant_scope_id) cover a
    target at (target_scope_type, target_scope_id)?

    This is the single source of truth for scope containment, used both
    for the ordinary permission Scope Check (AUTHORIZATION.md §5 step 2)
    and for delegation's possession/containment checks (§6.1/§6.3) --
    "possession at a scope equal to or broader than the target" and
    "scope containment" are the same underlying question.
    """
    if grant_scope_type == ScopeType.GLOBAL:
        return True

    if grant_scope_type == target_scope_type:
        if grant_scope_type in (ScopeType.GLOBAL, ScopeType.SELF):
            return True
        return grant_scope_id == target_scope_id

    # Different types: the grant can only cover a target of a genuinely
    # narrower tier, and only if the target actually sits inside the
    # grant's org unit per the real hierarchy.
    if _SCOPE_RANK[grant_scope_type] <= _SCOPE_RANK[target_scope_type]:
        return False

    if grant_scope_type == ScopeType.ORGANIZATION:
        if target_scope_type == ScopeType.DEPARTMENT:
            return _department_organization_id(target_scope_id) == grant_scope_id
        if target_scope_type == ScopeType.TEAM:
            return _team_organization_id(target_scope_id) == grant_scope_id
        if target_scope_type == ScopeType.SELF:
            # No scope_id to check against on either side (SELF is NULL
            # by definition) -- ranking says ORGANIZATION is broader than
            # SELF, and the concrete ownership match still has to be
            # verified separately at step 3 wherever the resource exists.
            return True

    if grant_scope_type == ScopeType.DEPARTMENT:
        if target_scope_type == ScopeType.TEAM:
            return _team_department_id(target_scope_id) == grant_scope_id
        if target_scope_type == ScopeType.SELF:
            return True

    if grant_scope_type == ScopeType.TEAM:
        if target_scope_type == ScopeType.SELF:
            return True

    return False
