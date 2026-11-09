"""
Centralized error handling.

Every error response — 400/404/405/500 from Phase 0, plus the
auth/authz errors added in Phase 2 (authorization) and Phase 3
(authentication, validation, rate limiting) — goes through this module
so the shape is consistent and no route has to hand-roll its own error
JSON. Internal exception details/stack traces are never exposed to the
client; they are only logged server-side.
"""
import logging

from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import HTTPException

from app.core.auth.exceptions import AuthenticationError, AuthenticationFailed
from app.permissions.exceptions import DelegationDeniedError, PermissionDeniedError
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.utils.responses import error_response

logger = logging.getLogger("polychem.errors")

_STATUS_TO_CODE = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_ERROR",
    403: "AUTHORIZATION_ERROR",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMITED",
}


def register_error_handlers(app):
    @app.errorhandler(400)
    def handle_400(err):
        return error_response("BAD_REQUEST", "The request was invalid.", 400)

    @app.errorhandler(404)
    def handle_404(err):
        return error_response("NOT_FOUND", "The requested resource was not found.", 404)

    @app.errorhandler(405)
    def handle_405(err):
        return error_response(
            "METHOD_NOT_ALLOWED", "This HTTP method is not allowed for this endpoint.", 405
        )

    @app.errorhandler(PydanticValidationError)
    def handle_pydantic_validation_error(err: PydanticValidationError):
        # Field-level detail is safe to return (it's about the shape of
        # the request, not any server/account state) and matches
        # SECURITY.md §4's "every request body validated through a
        # Pydantic schema before it reaches a service."
        details = [
            {"field": ".".join(str(part) for part in issue["loc"]), "message": issue["msg"]}
            for issue in err.errors()
        ]
        return error_response(
            "VALIDATION_ERROR", "The request could not be validated.", 400, details=details
        )

    @app.errorhandler(AuthenticationFailed)
    def handle_authentication_failed(err: AuthenticationFailed):
        # Login/refresh credential or token failures -- app/core/auth/
        # services.py guarantees `err.message` is already the same
        # generic string for every underlying cause (no enumeration).
        return error_response("AUTHENTICATION_ERROR", err.message, 401)

    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(err: AuthenticationError):
        # require_authenticated's JWT-validation failures (missing/
        # expired/invalid token, or a token for an inactive/deleted
        # user).
        return error_response("AUTHENTICATION_ERROR", err.message, 401)

    @app.errorhandler(PermissionDeniedError)
    def handle_permission_denied(err: PermissionDeniedError):
        # require_permission (Phase 2) raises this for both "no
        # authenticated user at all" (shouldn't normally reach here once
        # require_authenticated always runs first, but handled
        # defensively) and "authenticated but lacking the permission."
        if err.reason_code == "authentication_required":
            return error_response("AUTHENTICATION_ERROR", err.message, 401)
        return error_response("AUTHORIZATION_ERROR", err.message, 403)

    @app.errorhandler(DelegationDeniedError)
    def handle_delegation_denied(err: DelegationDeniedError):
        return error_response("AUTHORIZATION_ERROR", err.message, 403)

    @app.errorhandler(NotFoundError)
    def handle_not_found(err: NotFoundError):
        return error_response("NOT_FOUND", err.message, 404)

    @app.errorhandler(InvalidInputError)
    def handle_invalid_input(err: InvalidInputError):
        details = [{"field": err.field, "message": err.message}] if err.field else None
        return error_response("VALIDATION_ERROR", err.message, 400, details=details)

    @app.errorhandler(ConflictError)
    def handle_conflict(err: ConflictError):
        return error_response("CONFLICT", err.message, 409)

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        # Also catches Flask-Limiter's 429 (raised as a plain
        # werkzeug HTTPException) via _STATUS_TO_CODE above.
        code = _STATUS_TO_CODE.get(err.code, "HTTP_ERROR")
        return error_response(code, err.description or "Request failed.", err.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(err):
        # Log the real exception server-side only. The client never sees
        # the stack trace or exception message.
        logger.exception("Unhandled exception")
        return error_response(
            "INTERNAL_ERROR", "An unexpected error occurred.", 500
        )
