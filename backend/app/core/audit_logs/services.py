"""
Shared audit-logging helper -- SECURITY.md §7 / API.md §4: "Every
mutating endpoint writes an `audit_logs` entry via the shared
audit-logging service -- not opt-in per module, called from a shared
service-layer helper so it can't be forgotten."

Every Phase 4 resource service module calls `write_audit_log` at the end
of its create/update/delete function, inside the same DB transaction as
the mutation itself (this function only `add`s the row; it never commits
-- the caller's own `db.session.commit()` covers both the mutation and
the audit row atomically, so a rolled-back mutation never leaves an
orphan audit entry).
"""
from app.core.audit_logs.models import AuditLog
from app.extensions import db


def write_audit_log(
    *,
    user_id: int | None,
    action: str,
    module: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    `action` is a short verb such as "create"/"update"/"delete"/
    "delegate"/"revoke". `module` matches the permission-key module
    segment (e.g. "core", "authz"). `metadata` should be a plain,
    JSON-serializable diff/summary -- never a password, token, or hash.
    """
    row = AuditLog(
        user_id=user_id,
        action=action,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        event_metadata=metadata,
        ip_address=ip_address,
    )
    db.session.add(row)
    return row
