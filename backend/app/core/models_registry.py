"""
Single import point for every core/RBAC model.

SQLAlchemy only knows about a model class (and can build its relationships
/ include it in `db.metadata` for Alembic autogenerate and `db.create_all()`)
once the module defining it has been imported at least once. Rather than
relying on import order scattered across the app, every core model module
is imported here, and `app/__init__.py` imports this module once during
`create_app()` — before migrations, `create_all()`, or any blueprint
registration runs.

Phase 1 scope: identity, organizational hierarchy, and RBAC/grant tables
only. Business module models (tasks, crm, finance, ...) are added to this
same import point as each module is built, starting Phase 4a.
"""
from app.core.organizations.models import Organization  # noqa: F401
from app.core.departments.models import Department  # noqa: F401
from app.core.teams.models import Team, TeamMember  # noqa: F401
from app.core.users.models import User  # noqa: F401
from app.core.roles.models import Role  # noqa: F401
from app.core.permissions.models import Permission  # noqa: F401
from app.core.authorization.models import (  # noqa: F401
    ScopeType,
    PermissionEffect,
    UserRole,
    RolePermissionScope,
    UserPermissionScope,
    Delegation,
)
from app.core.auth.models import RefreshToken  # noqa: F401
from app.core.audit_logs.models import AuditLog  # noqa: F401
from app.modules.tasks.models import (  # noqa: F401
    Task,
    TaskAssignment,
    TaskAssignmentRule,
    TaskChecklistItem,
    TaskNote,
)
from app.modules.suppliers.models import Supplier, SupplierCategory, SupplierFile  # noqa: F401
from app.modules.customers.models import Customer, CustomerCategory, CustomerOptionItem  # noqa: F401
from app.modules.crm.models import CrmPaymentMethod, CrmSale  # noqa: F401
from app.modules.request_samples.models import (  # noqa: F401
    RequestSample, RequestSampleDispatch, RequestSampleEvent, RequestSampleFile, RequestSampleFollowUp,
    RequestSampleItem,
)
from app.modules.logistics.models import (  # noqa: F401
    LogisticsApplicant,
    LogisticsCompanyProfile,
    LogisticsDriverProfile,
    LogisticsFile,
    LogisticsServiceArea,
)
from app.modules.notifications.models import Notification  # noqa: F401

__all__ = [
    "Organization",
    "Department",
    "Team",
    "TeamMember",
    "User",
    "Role",
    "Permission",
    "ScopeType",
    "PermissionEffect",
    "UserRole",
    "RolePermissionScope",
    "UserPermissionScope",
    "Delegation",
    "RefreshToken",
    "AuditLog",
    "Task",
    "TaskAssignment",
    "TaskAssignmentRule",
    "TaskChecklistItem",
    "TaskNote",
    "Supplier",
    "SupplierCategory",
]