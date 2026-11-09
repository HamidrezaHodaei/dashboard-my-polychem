"""
`require_permission` -- ARCHITECTURE.md's `app/permissions/decorators.py`
("@require_permission('crm.customer.read', scope_resolver=...)").

Implements steps 1-2 of AUTHORIZATION.md §5's four-step resolution order
generically (Permission Check, Scope Check). Step 3 (Resource Ownership /
Organizational Relationship) is inherently resource-specific -- it needs
the actual target row (e.g. a task's assignee list) -- so it is NOT
implemented here; a caller that needs it performs that check itself
after this decorator's step 1-2 check passes, once a real resource
exists (Phase 3/4+). Step 4 (Allow/Deny) is simply "did steps 1-3 all
pass" -- there is nothing left to add at that point beyond what this
decorator and the caller already do.

No business module exists yet in Phase 2, so this decorator is
deliberately generic and is NOT coupled to any specific module's
resource shape (per instruction). Its only contract is:

    scope_resolver(*args, **kwargs) -> (ScopeType, scope_id) | None

`scope_resolver` is optional. When omitted, only step 1 (permission held
at all, any scope) is checked -- appropriate for permissions that are
inherently GLOBAL-only, or for a caller that will do its own scope/
ownership check afterward.

There is also no authentication layer yet (Phase 3), so this decorator
has to get the acting user from *somewhere*. The minimal, most neutral
place is `flask.g.current_user` -- a Flask-idiomatic slot Phase 3's auth
middleware is expected to populate per request. This is the one
necessary point of coupling to a not-yet-built layer; it names no
business module and makes no assumption about *how* `g.current_user`
gets set, only that it will be. Tests in this phase set it directly.
"""
from functools import wraps
from typing import Callable

from flask import g

from app.core.authorization.models import ScopeType
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission

ScopeResolver = Callable[..., tuple[ScopeType, int | None] | None]


def require_permission(permission_key: str, scope_resolver: ScopeResolver | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if user is None:
                raise PermissionDeniedError(
                    "authentication_required",
                    "No authenticated user is available for this request.",
                )

            target_scope_type = None
            target_scope_id = None
            if scope_resolver is not None:
                resolved = scope_resolver(*args, **kwargs)
                if resolved is not None:
                    target_scope_type, target_scope_id = resolved

            if not has_permission(user, permission_key, target_scope_type, target_scope_id):
                raise PermissionDeniedError(
                    "permission_denied",
                    f"Missing permission '{permission_key}' for this action.",
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator
