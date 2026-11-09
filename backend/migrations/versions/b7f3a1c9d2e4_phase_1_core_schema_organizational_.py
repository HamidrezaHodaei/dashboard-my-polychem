"""Phase 1: core schema - identity, organizational hierarchy, scoped RBAC

Revision ID: b7f3a1c9d2e4
Revises: d60fbb96f2a7
Create Date: 2026-09-15 00:00:00.000000

NOTE ON HOW THIS MIGRATION WAS PRODUCED
----------------------------------------
This migration was hand-written to mirror app/core/*/models.py exactly,
NOT produced by `alembic revision --autogenerate` / `flask db migrate` —
the sandbox this was developed in has no network access and could not
install Flask-SQLAlchemy/Flask-Migrate/Alembic to run that command. Before
relying on this migration, run `flask db migrate` locally against an
up-to-date checkout to confirm autogenerate produces no diff against this
file (see the accompanying report for the exact verification commands).

Table creation order and the two deferred ALTER TABLE statements at the
end exist specifically to resolve one circular dependency:
`departments.manager_user_id` / `teams.manager_user_id` both reference
`users.id`, while `users.organization_id` / `users.department_id`
reference `organizations.id` / `departments.id`. departments/teams are
created first with those two manager columns present but unconstrained;
users is created next; the two FK constraints are added last via
`op.create_foreign_key`, matching the `use_alter=True` markers on those
columns in the ORM models.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'b7f3a1c9d2e4'
down_revision = 'd60fbb96f2a7'
branch_labels = None
depends_on = None


# DATABASE.md: "PK: id BIGINT UNSIGNED AUTO_INCREMENT" and every FK that
# points at one. Portable generic BigInteger everywhere except MySQL,
# where it renders as BIGINT UNSIGNED — mirrors app/core/base.py's
# BigIntUnsigned type exactly.
BIGINT_UNSIGNED = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")

SCOPE_TYPE_VALUES = ("GLOBAL", "ORGANIZATION", "DEPARTMENT", "TEAM", "SELF")


def upgrade():
    # ---------------------------------------------------------------
    # 1. organizations
    # ---------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("parent_organization_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_organization_id"], ["organizations.id"],
            name="fk_organizations_parent_organization_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ---------------------------------------------------------------
    # 2. roles
    # ---------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("name", name="uq_roles_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ---------------------------------------------------------------
    # 3. permissions
    # ---------------------------------------------------------------
    op.create_table(
        "permissions",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=150), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("resource", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("is_delegable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("key", name="uq_permissions_key"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ---------------------------------------------------------------
    # 4. departments (manager_user_id present, FK deferred — see module docstring)
    # ---------------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("organization_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("parent_department_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("manager_user_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_departments_organization_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_department_id"], ["departments.id"],
            name="fk_departments_parent_department_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_index("ix_departments_parent_department_id", "departments", ["parent_department_id"])

    # ---------------------------------------------------------------
    # 5. teams (manager_user_id present, FK deferred)
    # ---------------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("department_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("manager_user_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"],
            name="fk_teams_department_id", ondelete="CASCADE",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_teams_department_id", "teams", ["department_id"])

    # ---------------------------------------------------------------
    # 6. users
    # ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("organization_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("department_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_users_organization_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"],
            name="fk_users_department_id", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ---------------------------------------------------------------
    # 7. Deferred FKs now that both sides of the cycle exist.
    # ---------------------------------------------------------------
    op.create_foreign_key(
        "fk_departments_manager_user_id", "departments", "users",
        ["manager_user_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_teams_manager_user_id", "teams", "users",
        ["manager_user_id"], ["id"], ondelete="RESTRICT",
    )

    # ---------------------------------------------------------------
    # 8. team_members
    # ---------------------------------------------------------------
    op.create_table(
        "team_members",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("team_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["team_id"], ["teams.id"],
            name="fk_team_members_team_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_team_members_user_id", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )

    # ---------------------------------------------------------------
    # 9. user_roles
    # ---------------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("role_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("organization_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_roles_user_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name="fk_user_roles_role_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_user_roles_organization_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # ---------------------------------------------------------------
    # 10. role_permission_scopes
    # ---------------------------------------------------------------
    op.create_table(
        "role_permission_scopes",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("role_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("permission_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column(
            "scope_type",
            sa.Enum(*SCOPE_TYPE_VALUES, name="role_permission_scopes_scope_type"),
            nullable=False,
        ),
        sa.Column("scope_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("granted_by_user_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name="fk_role_permission_scopes_role_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"],
            name="fk_role_permission_scopes_permission_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"], ["users.id"],
            name="fk_role_permission_scopes_granted_by_user_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_role_permission_scopes_role_permission", "role_permission_scopes",
        ["role_id", "permission_id"],
    )
    op.create_index(
        "ix_role_permission_scopes_scope", "role_permission_scopes",
        ["scope_type", "scope_id"],
    )

    # ---------------------------------------------------------------
    # 11. user_permission_scopes
    # ---------------------------------------------------------------
    op.create_table(
        "user_permission_scopes",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("permission_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column(
            "scope_type",
            sa.Enum(*SCOPE_TYPE_VALUES, name="user_permission_scopes_scope_type"),
            nullable=False,
        ),
        sa.Column("scope_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("granted_by_user_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_permission_scopes_user_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"],
            name="fk_user_permission_scopes_permission_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"], ["users.id"],
            name="fk_user_permission_scopes_granted_by_user_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_user_permission_scopes_user_permission", "user_permission_scopes",
        ["user_id", "permission_id"],
    )
    op.create_index(
        "ix_user_permission_scopes_scope", "user_permission_scopes",
        ["scope_type", "scope_id"],
    )

    # ---------------------------------------------------------------
    # 12. delegations
    # ---------------------------------------------------------------
    op.create_table(
        "delegations",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("delegator_user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("delegatee_user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("resulting_user_permission_scope_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("delegated_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by_user_id", BIGINT_UNSIGNED, nullable=True),
        sa.ForeignKeyConstraint(
            ["delegator_user_id"], ["users.id"],
            name="fk_delegations_delegator_user_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delegatee_user_id"], ["users.id"],
            name="fk_delegations_delegatee_user_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_user_permission_scope_id"], ["user_permission_scopes.id"],
            name="fk_delegations_resulting_user_permission_scope_id", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"], ["users.id"],
            name="fk_delegations_revoked_by_user_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_delegations_delegator_user_id", "delegations", ["delegator_user_id"])
    op.create_index("ix_delegations_delegatee_user_id", "delegations", ["delegatee_user_id"])

    # ---------------------------------------------------------------
    # 13. refresh_tokens
    # ---------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIGINT_UNSIGNED, nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by_token_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_refresh_tokens_user_id", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"], ["refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by_token_id", ondelete="SET NULL",
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ---------------------------------------------------------------
    # 14. audit_logs
    # ---------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", BIGINT_UNSIGNED, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", BIGINT_UNSIGNED, nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_audit_logs_user_id", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("delegations")
    op.drop_table("user_permission_scopes")
    op.drop_table("role_permission_scopes")
    op.drop_table("user_roles")
    op.drop_table("team_members")

    op.drop_constraint("fk_teams_manager_user_id", "teams", type_="foreignkey")
    op.drop_constraint("fk_departments_manager_user_id", "departments", type_="foreignkey")

    op.drop_table("users")
    op.drop_table("teams")
    op.drop_table("departments")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("organizations")
