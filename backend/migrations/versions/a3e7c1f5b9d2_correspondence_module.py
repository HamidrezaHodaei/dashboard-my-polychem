"""correspondence (مکاتبات سازمانی): messages, participants, attachments, unit access + permissions

Permissions (correspondence.mail.{read,create,update,delete}) are created and granted to the `admin`
role; everybody else gets them from the permission matrix ("مکاتبات" row) or through an organizational
unit switched on in `mail_unit_access`.

Revision ID: a3e7c1f5b9d2
Revises: b8e3a5c7d9f1
Create Date: 2026-11-17 09:00:00
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "a3e7c1f5b9d2"
down_revision = "b8e3a5c7d9f1"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
LONGTEXT = sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")
ACTIONS = ("create", "read", "update", "delete")


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ]


permissions = sa.table(
    "permissions",
    sa.column("id", sa.BigInteger), sa.column("key", sa.String), sa.column("module", sa.String),
    sa.column("resource", sa.String), sa.column("action", sa.String), sa.column("is_delegable", sa.Boolean),
    sa.column("description", sa.String), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("name", sa.String))
role_scopes = sa.table(
    "role_permission_scopes",
    sa.column("id", sa.BigInteger), sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger),
    sa.column("scope_type", sa.String), sa.column("scope_id", sa.BigInteger), sa.column("is_active", sa.Boolean),
    sa.column("granted_by_user_id", sa.BigInteger), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)


def upgrade():
    op.create_table(
        "mail_messages",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("thread_id", BIG),
        sa.Column("parent_id", BIG, sa.ForeignKey("mail_messages.id", ondelete="SET NULL")),
        sa.Column("sender_id", BIG, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False, server_default=""),
        sa.Column("body", LONGTEXT, nullable=False),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("draft_recipients", sa.Text()),
        sa.Column("sent_at", sa.DateTime()),
        *_ts(),
    )
    op.create_index("ix_mail_messages_thread", "mail_messages", ["thread_id", "id"])
    op.create_index("ix_mail_messages_sender", "mail_messages", ["sender_id"])

    op.create_table(
        "mail_participants",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("message_id", BIG, sa.ForeignKey("mail_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("folder", sa.String(10), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("labels", sa.String(120), nullable=False, server_default=""),
        sa.Column("purged_at", sa.DateTime()),
        sa.Column("read_at", sa.DateTime()),
        *_ts(),
        sa.UniqueConstraint("message_id", "user_id", name="uq_mail_participants_message_user"),
    )
    op.create_index("ix_mail_participants_user_folder", "mail_participants", ["user_id", "folder", "is_read"])
    op.create_index("ix_mail_participants_message", "mail_participants", ["message_id"])

    op.create_table(
        "mail_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", BIG, sa.ForeignKey("mail_messages.id", ondelete="CASCADE")),
        sa.Column("uploaded_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(80), nullable=False),
        sa.Column("content_type", sa.String(120)),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        *_ts(),
    )
    op.create_index("ix_mail_attachments_message", "mail_attachments", ["message_id"])

    op.create_table(
        "mail_unit_access",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("department_id", BIG, sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("granted_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_ts(),
        sa.UniqueConstraint("department_id", name="uq_mail_unit_access_department"),
    )

    _seed_permissions()


def _seed_permissions():
    """Idempotent: only inserts what is missing (same approach as the supplier / request-sample seeds)."""
    bind = op.get_bind()
    now = datetime.utcnow()
    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    for action in ACTIONS:
        key = f"correspondence.mail.{action}"
        perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if perm_id is None:
            bind.execute(permissions.insert().values(
                key=key, module="correspondence", resource="mail", action=action, is_delegable=True,
                description=f"{action.capitalize()} correspondence mail records.", created_at=now, updated_at=now,
            ))
            perm_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
        if admin_id is None:
            continue
        grant = bind.execute(sa.select(role_scopes.c.id).where(
            role_scopes.c.role_id == admin_id, role_scopes.c.permission_id == perm_id,
            role_scopes.c.scope_type == "GLOBAL",
        )).first()
        if grant is None:
            bind.execute(role_scopes.insert().values(
                role_id=admin_id, permission_id=perm_id, scope_type="GLOBAL", scope_id=None, is_active=True,
                granted_by_user_id=None, created_at=now, updated_at=now,
            ))
        else:
            bind.execute(role_scopes.update().where(role_scopes.c.id == grant[0]).values(is_active=True))


def downgrade():
    op.drop_table("mail_unit_access")
    op.drop_index("ix_mail_attachments_message", table_name="mail_attachments")
    op.drop_table("mail_attachments")
    op.drop_index("ix_mail_participants_message", table_name="mail_participants")
    op.drop_index("ix_mail_participants_user_folder", table_name="mail_participants")
    op.drop_table("mail_participants")
    op.drop_index("ix_mail_messages_sender", table_name="mail_messages")
    op.drop_index("ix_mail_messages_thread", table_name="mail_messages")
    op.drop_table("mail_messages")
    # The seeded permission rows are intentionally kept (same reasoning as the other seed migrations).
