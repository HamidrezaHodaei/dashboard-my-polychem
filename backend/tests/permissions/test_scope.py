"""
Scope containment tests -- app/permissions/scope.py.

Covers: GLOBAL, ORGANIZATION, DEPARTMENT, TEAM, SELF; equal scope;
broader-covers-narrower; narrower-does-NOT-cover-broader (the exact
shape of a privilege-escalation attempt); and that containment for
ORGANIZATION/DEPARTMENT/TEAM is resolved via the real hierarchy tables
(a same-tier scope in a *different* org/department is NOT covered).
"""
from app.core.authorization.models import ScopeType
from app.permissions.scope import scope_covers

from .factories import make_department, make_organization, make_team


def test_global_covers_everything(app):
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    assert scope_covers(ScopeType.GLOBAL, None, ScopeType.GLOBAL, None) is True
    assert scope_covers(ScopeType.GLOBAL, None, ScopeType.ORGANIZATION, org.id) is True
    assert scope_covers(ScopeType.GLOBAL, None, ScopeType.DEPARTMENT, dept.id) is True
    assert scope_covers(ScopeType.GLOBAL, None, ScopeType.TEAM, team.id) is True
    assert scope_covers(ScopeType.GLOBAL, None, ScopeType.SELF, None) is True


def test_organization_covers_its_own_department_and_team(app):
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    assert scope_covers(ScopeType.ORGANIZATION, org.id, ScopeType.ORGANIZATION, org.id) is True
    assert scope_covers(ScopeType.ORGANIZATION, org.id, ScopeType.DEPARTMENT, dept.id) is True
    assert scope_covers(ScopeType.ORGANIZATION, org.id, ScopeType.TEAM, team.id) is True
    assert scope_covers(ScopeType.ORGANIZATION, org.id, ScopeType.SELF, None) is True


def test_organization_does_not_cover_a_different_organizations_department(app):
    org_a = make_organization()
    org_b = make_organization()
    dept_under_b = make_department(org_b)

    assert scope_covers(ScopeType.ORGANIZATION, org_a.id, ScopeType.DEPARTMENT, dept_under_b.id) is False


def test_department_covers_its_own_team(app):
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    assert scope_covers(ScopeType.DEPARTMENT, dept.id, ScopeType.DEPARTMENT, dept.id) is True
    assert scope_covers(ScopeType.DEPARTMENT, dept.id, ScopeType.TEAM, team.id) is True
    assert scope_covers(ScopeType.DEPARTMENT, dept.id, ScopeType.SELF, None) is True


def test_department_does_not_cover_a_team_in_a_sibling_department(app):
    org = make_organization()
    dept_a = make_department(org)
    dept_b = make_department(org)
    team_under_b = make_team(dept_b)

    assert scope_covers(ScopeType.DEPARTMENT, dept_a.id, ScopeType.TEAM, team_under_b.id) is False


def test_department_does_not_cover_its_parent_organization(app):
    org = make_organization()
    dept = make_department(org)

    assert scope_covers(ScopeType.DEPARTMENT, dept.id, ScopeType.ORGANIZATION, org.id) is False


def test_team_covers_only_itself_and_self(app):
    org = make_organization()
    dept = make_department(org)
    team_a = make_team(dept)
    team_b = make_team(dept)

    assert scope_covers(ScopeType.TEAM, team_a.id, ScopeType.TEAM, team_a.id) is True
    assert scope_covers(ScopeType.TEAM, team_a.id, ScopeType.SELF, None) is True
    # Sibling team under the same department is NOT covered.
    assert scope_covers(ScopeType.TEAM, team_a.id, ScopeType.TEAM, team_b.id) is False
    # A team scope never covers its parent department.
    assert scope_covers(ScopeType.TEAM, team_a.id, ScopeType.DEPARTMENT, dept.id) is False


def test_self_covers_only_self(app):
    assert scope_covers(ScopeType.SELF, None, ScopeType.SELF, None) is True


def test_narrower_scope_never_covers_a_broader_target(app):
    """The exact shape of a privilege-escalation attempt at the scope
    layer: holding TEAM must never satisfy a DEPARTMENT/ORGANIZATION/
    GLOBAL target, and holding DEPARTMENT must never satisfy ORGANIZATION
    or GLOBAL."""
    org = make_organization()
    dept = make_department(org)
    team = make_team(dept)

    assert scope_covers(ScopeType.SELF, None, ScopeType.TEAM, team.id) is False
    assert scope_covers(ScopeType.TEAM, team.id, ScopeType.ORGANIZATION, org.id) is False
    assert scope_covers(ScopeType.DEPARTMENT, dept.id, ScopeType.GLOBAL, None) is False
    assert scope_covers(ScopeType.ORGANIZATION, org.id, ScopeType.GLOBAL, None) is False
