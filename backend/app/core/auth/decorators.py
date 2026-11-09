"""
`require_authenticated` -- Phase 3's ONLY authentication decorator.

Its job, per the approved decisions, is exactly and only:
    1. validate the access JWT
    2. extract the user id from `sub`
    3. load the User ORM object
    4. verify the user is active and not soft-deleted
    5. set `g.current_user`
    6. allow the protected route to continue

No role/permission/scope resolution happens here -- that is exclusively
Phase 2's job (`app/permissions/*`), untouched by this file.
`app/permissions/decorators.py::require_permission` already reads
`g.current_user` from this exact slot (its own docstring, written in
Phase 2, anticipated this). Stack the two decorators to compose
authentication and authorization:

    @app.route(...)
    @require_authenticated
    @require_permission("some.permission.key")
    def view(): ...

(`require_authenticated` must be the outer decorator so it runs first
and populates `g.current_user` before `require_permission` reads it.)
"""
from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException, NoAuthorizationError
from jwt import ExpiredSignatureError, PyJWTError

from app.core.auth.exceptions import AuthenticationError
from app.core.users.models import User
from app.extensions import db


def _authenticate_current_request() -> User:
    try:
        verify_jwt_in_request()
    except NoAuthorizationError as exc:
        raise AuthenticationError(
            "missing_token", "Authentication token is required."
        ) from exc
    except ExpiredSignatureError as exc:
        raise AuthenticationError(
            "token_expired", "Authentication token has expired."
        ) from exc
    except (JWTExtendedException, PyJWTError) as exc:
        # Catches malformed/invalid-signature/wrong-type and any other
        # Flask-JWT-Extended or underlying PyJWT failure not already
        # handled above -- deliberately broad since decode failures can
        # surface as either library's exception type depending on
        # exactly what's wrong with the token.
        raise AuthenticationError(
            "invalid_token", "Invalid authentication token."
        ) from exc

    claims = get_jwt()
    if claims.get("type") != "access":
        raise AuthenticationError("invalid_token", "Invalid authentication token.")

    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("invalid_token", "Invalid authentication token.") from exc

    user = db.session.get(User, user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        # Deliberately the same message/reason_code as a structurally
        # invalid token -- a token that decodes fine but points at a
        # deactivated/deleted/nonexistent user is just as unusable, and
        # distinguishing them in the response would leak account state.
        raise AuthenticationError("invalid_token", "Invalid authentication token.")

    return user


def require_authenticated(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = _authenticate_current_request()
        return fn(*args, **kwargs)

    return wrapper
