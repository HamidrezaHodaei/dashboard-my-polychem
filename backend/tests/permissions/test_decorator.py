"""
`require_permission` decorator tests -- app/permissions/decorators.py.

No business module/route exists yet, so these exercise the decorator
directly against a plain function, with `flask.g.current_user` set
manually (standing in for Phase 3's future auth middleware) and a
minimal fake `scope_resolver` (standing in for a future module's
resource lookup) -- never a real business-module resource shape, per
instruction to keep the decorator generic.
"""
import pytest
from flask import g

from app.core.authorization.models import ScopeType
from app.permissions.decorators import require_permission
from app.permissions.exceptions import PermissionDeniedError

from .factories import grant_user_permission, make_department, make_organization, make_permission, make_user


def test_require_permission_denies_when_no_current_user(app):
    @require_permission("tasks.task.read")
    def view():  # pragma: no cover - should never execute
        return "ok"

    with app.test_request_context():
        g.current_user = None
        with pytest.raises(PermissionDeniedError) as exc_info:
            view()
        assert exc_info.value.reason_code == "authentication_required"


def test_require_permission_denies_when_permission_missing(app):
    user = make_user()

    @require_permission("tasks.task.read")
    def view():  # pragma: no cover
        return "ok"

    with app.test_request_context():
        g.current_user = user
        with pytest.raises(PermissionDeniedError) as exc_info:
            view()
        assert exc_info.value.reason_code == "permission_denied"


def test_require_permission_allows_when_permission_held_no_scope(app):
    user = make_user()
    permission = make_permission("tasks.task.read")
    grant_user_permission(user, permission, ScopeType.GLOBAL)

    @require_permission("tasks.task.read")
    def view():
        return "ok"

    with app.test_request_context():
        g.current_user = user
        assert view() == "ok"


def test_require_permission_uses_scope_resolver(app):
    user = make_user()
    org = make_organization()
    dept = make_department(org)
    other_dept = make_department(org)
    permission = make_permission("tasks.task.create")
    grant_user_permission(user, permission, ScopeType.DEPARTMENT, dept.id)

    def resolve_to(department_id):
        return (ScopeType.DEPARTMENT, department_id)

    @require_permission("tasks.task.create", scope_resolver=lambda department_id: resolve_to(department_id))
    def view(department_id):
        return "ok"

    with app.test_request_context():
        g.current_user = user
        assert view(dept.id) == "ok"
        with pytest.raises(PermissionDeniedError) as exc_info:
            view(other_dept.id)
        assert exc_info.value.reason_code == "permission_denied"
