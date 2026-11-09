"""
RBAC + Scope engine (Phase 2) -- module-agnostic, per ARCHITECTURE.md §4.

    registry.py     canonical, documented permission keys only (see that
                     module's docstring for what is and is not defined)
    scope.py         scope containment/expansion over the real
                     organizational hierarchy (GLOBAL>ORG>DEPT>TEAM>SELF)
    service.py       Effective Grants(user) = role grants UNION user
                     grants (AUTHORIZATION.md §5), and the permission+
                     scope check built on top of it
    delegation.py    user-targeted delegation eligibility (five checks
                     plus the self-delegation guard) and lifecycle
    decorators.py    `require_permission` -- generic, route-agnostic

No HTTP routes are registered from this package in Phase 2
(IMPLEMENTATION_PLAN.md: "works as a library, independent of any
route"). Phase 3/4 wire `require_permission` into actual blueprints.
"""
