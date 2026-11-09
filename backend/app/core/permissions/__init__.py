"""
Permission catalog model (DATABASE.md — RBAC tables > permissions).

Not to be confused with app/permissions/ (top-level) — that package is the
RBAC + Scope *engine* (registry, service, scope resolution, decorators),
implemented starting Phase 2. This package holds only the `Permission`
database model itself, per ARCHITECTURE.md's `core/permissions/` folder.
"""
