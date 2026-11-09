"""
Grant / association tables that connect users, roles, and permissions:
UserRole, RolePermissionScope, UserPermissionScope, Delegation.

DESIGN NOTE (Phase 1): ARCHITECTURE.md's folder sketch does not list a
dedicated `core/authorization/` package by name (it lists core/auth,
users, roles, permissions, organizations, departments, teams, audit_logs).
These four tables are relationship/grant data that doesn't belong to any
single one of those entities — grouping them here (rather than bolting
`RolePermissionScope` onto roles/models.py and `UserPermissionScope` +
`Delegation` onto users/models.py) keeps each entity's own module focused
on its own identity data. This is a structural judgment call for review,
not a deviation from any schema/behavior in DATABASE.md or AUTHORIZATION.md
— every column, FK, index, and constraint below matches those documents
exactly. No permission-evaluation logic lives here; that is Phase 2's
app/permissions/ engine.
"""
