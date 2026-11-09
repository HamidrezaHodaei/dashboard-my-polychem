"""
Shared test-data builders and HTTP helpers for Phase 4's CRUD/delegation
route tests.

Re-exports everything from tests/permissions/factories.py (org/dept/
team/user/role/permission/grant builders -- identical needs here) and
adds `auth_headers`, which mints a real access JWT directly via
Flask-JWT-Extended rather than going through POST /api/auth/login --
faster, and Phase 4 tests care about permission/scope outcomes, not
login itself (already covered by tests/auth/).
"""
from flask_jwt_extended import create_access_token

# Re-export every Phase 2 builder so Phase 4 tests only need one import.
from tests.permissions.factories import (  # noqa: F401
    add_team_member,
    assign_role,
    grant_role_permission,
    grant_user_permission,
    make_department,
    make_organization,
    make_permission,
    make_role,
    make_team,
    make_user,
)


def auth_headers(user) -> dict:
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}
