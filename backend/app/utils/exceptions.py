"""
Shared, module-agnostic service-layer exceptions for Phase 4's core CRUD
modules.

Plain Python exceptions, not Flask/Werkzeug HTTPExceptions -- consistent
with app/permissions/exceptions.py and app/core/auth/exceptions.py, so
the HTTP status/error-code mapping stays centralized in
app/middleware/error_handlers.py rather than scattered across every
resource's service module.
"""


class NotFoundError(Exception):
    """
    Raised by a Phase 4 service function when a requested row does not
    exist (never returned) or is soft-deleted (treated as gone for every
    ordinary read/update/delete path -- a soft-deleted row is not a
    valid target for further mutation). Maps to 404 NOT_FOUND.
    """

    def __init__(self, message: str = "The requested resource was not found."):
        self.message = message
        super().__init__(message)


class ConflictError(Exception):
    """
    Raised when a request is well-formed and permitted but conflicts
    with the current state of the data -- a duplicate unique value
    (email/username/role name/permission key), an attempt to delete a
    row that is still referenced by active children (an organization
    with active departments, a permission still granted to a role or
    user), or an attempt to delete/rename-away-from a protected system
    row (a system role). Maps to 409 CONFLICT.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidInputError(Exception):
    """A query/body value that is syntactically fine for the framework but not acceptable
    to the business rules (an impossible date, from > to, ...). Maps to 400 VALIDATION_ERROR
    with the same `details` shape the Pydantic handler produces."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)

