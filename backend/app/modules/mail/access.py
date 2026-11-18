"""
Who may use correspondence, enforced on the server for every mail endpoint.

A user may use an action (`read` / `create` / `update` / `delete`) when ANY of these holds, and
none of the blockers below applies:

  1. a role or direct grant of `correspondence.mail.<action>` -- managed by the admin in the ordinary
     per-role / per-user permission matrix ("مکاتبات" row);
  2. the user belongs to an organizational unit the admin switched on for mail
     (`mail_unit_access`): their own department (users.department_id) or the department of a team
     they are a member of. A unit grants the four everyday actions on the user's OWN mailbox.

Blocker: an explicit per-user DENY of that permission (the unchecked cell in the user's matrix) beats
a unit grant, exactly like it beats a role grant everywhere else (app/permissions/service.py).

Nobody ever gets to see another user's mail through this module: every query is filtered by the
acting user's own participant row (services.py), whatever the permission is.
"""
from app.core.authorization.models import PermissionEffect, UserPermissionScope
from app.core.permissions.models import Permission
from app.core.teams.models import Team, TeamMember
from app.core.users.models import User
from app.extensions import db
from app.modules.mail.models import MailUnitAccess
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission

ACTIONS = ("read", "create", "update", "delete")
MODULE_KEY = "correspondence.mail"


def permission_key(action: str) -> str:
    return f"{MODULE_KEY}.{action}"


def user_unit_ids(user: User) -> set[int]:
    """Departments the user belongs to: their own plus the departments of their teams."""
    ids: set[int] = set()
    if user.department_id:
        ids.add(int(user.department_id))
    rows = (
        db.session.query(Team.department_id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .filter(TeamMember.user_id == user.id, Team.deleted_at.is_(None))
        .all()
    )
    ids.update(int(r[0]) for r in rows if r[0])
    return ids


def enabled_unit_ids() -> set[int]:
    return {int(r[0]) for r in db.session.query(MailUnitAccess.department_id).all()}


def unit_grants_access(user: User) -> bool:
    units = user_unit_ids(user)
    return bool(units) and bool(units & enabled_unit_ids())


def _has_user_deny(user: User, key: str) -> bool:
    return (
        db.session.query(UserPermissionScope.id)
        .join(Permission, Permission.id == UserPermissionScope.permission_id)
        .filter(
            UserPermissionScope.user_id == user.id,
            UserPermissionScope.effect == PermissionEffect.DENY,
            UserPermissionScope.is_active.is_(True),
            Permission.key == key,
        )
        .first()
        is not None
    )


def can(user: User, action: str) -> bool:
    key = permission_key(action)
    if has_permission(user, key, None, None):
        return True
    if _has_user_deny(user, key):
        return False
    return unit_grants_access(user)


def can_read_mail(user: User) -> bool:
    return can(user, "read")


def access_summary(user: User) -> dict:
    return {action: can(user, action) for action in ACTIONS}


def require(user: User, action: str) -> None:
    if not can(user, action):
        raise PermissionDeniedError(
            "permission_denied", f"Missing permission '{permission_key(action)}' for this action."
        )


def can_manage_access(user: User) -> bool:
    """Choosing which units may use mail is permission management."""
    return has_permission(user, "core.permission.update", None, None)


def require_manage_access(user: User) -> None:
    if not can_manage_access(user):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'core.permission.update' for this action."
        )
