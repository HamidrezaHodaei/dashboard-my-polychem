"""
Authentication exception types (Phase 3). These are distinct from
`app/permissions/exceptions.py`'s `PermissionDeniedError`/
`DelegationDeniedError` -- those are Phase 2's *authorization* failures
(you're who you say you are, but not allowed to do this); these are
*authentication* failures (we can't establish who you are, or your
credentials/token don't check out). Both families end up mapped to
error-envelope responses in `app/middleware/error_handlers.py`, kept as
separate classes so each layer stays honest about what it's reporting.

Plain Python exceptions, not Flask/Werkzeug HTTPExceptions -- consistent
with Phase 2's own exceptions.py, so the HTTP status/code mapping stays
centralized in error_handlers.py rather than scattered across services.
"""


class AuthenticationError(Exception):
    """
    Raised by `app/core/auth/decorators.py::require_authenticated` when
    the access token itself is missing, malformed, expired, or points at
    a user who is no longer active/exists. Carries a machine-readable
    `reason_code` for tests/logging; the client-facing `message` is safe
    to return as-is (never leaks internals).
    """

    def __init__(self, reason_code: str, message: str):
        self.reason_code = reason_code
        self.message = message
        super().__init__(message)


class AuthenticationFailed(Exception):
    """
    Raised by `app/core/auth/services.py` for login/refresh credential or
    token failures. Per SECURITY.md / the approved Phase 3 decisions, the
    *message* must be identical regardless of the underlying reason
    (unknown identifier, wrong password, inactive user, soft-deleted
    user, missing/expired/revoked/reused refresh token) -- callers must
    never construct a different message per case, to avoid user/token
    enumeration.
    """

    def __init__(self, message: str = "Invalid credentials."):
        self.message = message
        super().__init__(message)
