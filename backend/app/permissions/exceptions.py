"""
Phase 2 exception types.

These are plain Python exceptions, not Flask/Werkzeug HTTPExceptions.
Phase 2 is a library with no HTTP routes (IMPLEMENTATION_PLAN.md Phase 2:
"the authorization engine ... works as a library, independent of any
route"), so mapping these to HTTP status codes / the API.md error
envelope (401/403, AUTHENTICATION_ERROR/AUTHORIZATION_ERROR) is left to
whichever future phase actually wires a route to `require_permission`
(Phase 3/4) — that mapping belongs in app/middleware/error_handlers.py at
that point, not here.
"""


class PermissionDeniedError(Exception):
    """
    Raised by `require_permission` (decorators.py) when the four-step
    check fails. Carries a machine-readable `reason_code` so a future
    HTTP layer can decide status codes/messages without string-matching.
    """

    def __init__(self, reason_code: str, message: str):
        self.reason_code = reason_code
        self.message = message
        super().__init__(message)


class DelegationDeniedError(Exception):
    """
    Raised by `create_delegation` (delegation.py) when any of the
    eligibility checks in AUTHORIZATION.md §6/§9 fails. `reason_code`
    matches one of the codes documented on `DelegationCheckResult`
    in delegation.py.
    """

    def __init__(self, reason_code: str, message: str):
        self.reason_code = reason_code
        self.message = message
        super().__init__(message)
