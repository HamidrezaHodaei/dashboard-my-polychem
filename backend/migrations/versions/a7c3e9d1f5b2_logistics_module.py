"""logistics module -- transport-company / driver registration

Creates the five logistics tables, then seeds (idempotently):
  * the `logistics.{company,driver}.{create,read,update,delete,review}` permissions,
  * GLOBAL grants of all of them to the `admin` role,
  * three ready-made roles so access levels work out of the box:
        logistics_manager   -- everything, both applicant types
        logistics_operator  -- read/create/update, both types (no delete, no review)
        logistics_viewer    -- read only, both types
    (Per-type or per-user variations are done in the existing permission matrix.)

Revision ID: a7c3e9d1f5b2
Revises: b3c7e1d5a9f4
Create Date: 2026-10-29 00:00:00
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "a7c3e9d1f5b2"
down_revision = "b3c7e1d5a9f4"
branch_labels = None
depends_on = None

BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
JSON_TYPE = sa.JSON().with_variant(mysql.JSON(), "mysql")


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ]


def _applicant_fk():
    return sa.Column(
        "applicant_id", BIG, sa.ForeignKey("logistics_applicants.id", ondelete="CASCADE"), nullable=False, unique=True
    )


def upgrade():
    op.create_table(
        "logistics_applicants",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        sa.Column("applicant_type", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="PENDING"),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("mobile", sa.String(length=11), nullable=False),
        sa.Column("is_public_submission", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        *_ts(),
    )
    op.create_index("ix_logistics_applicants_type_status", "logistics_applicants", ["applicant_type", "status"])
    op.create_index("ix_logistics_applicants_type_mobile", "logistics_applicants", ["applicant_type", "mobile"])

    op.create_table(
        "logistics_company_profiles",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        _applicant_fk(),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("national_id", sa.String(length=11), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("office_address", sa.Text(), nullable=False),
        sa.Column("rep_first_name", sa.String(length=100), nullable=False),
        sa.Column("rep_last_name", sa.String(length=100), nullable=False),
        sa.Column("rep_position", sa.String(length=30), nullable=False),
        sa.Column("rep_position_other", sa.String(length=100), nullable=True),
        sa.Column("rep_mobile", sa.String(length=11), nullable=False),
        sa.Column("rep_landline", sa.String(length=11), nullable=True),
        *_ts(),
    )
    op.create_index("ix_logistics_company_profiles_national_id", "logistics_company_profiles", ["national_id"])
    op.create_index("ix_logistics_company_province_city", "logistics_company_profiles", ["province", "city"])

    op.create_table(
        "logistics_driver_profiles",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        _applicant_fk(),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("national_code", sa.String(length=10), nullable=False),
        sa.Column("mobile", sa.String(length=11), nullable=False),
        sa.Column("alt_phone", sa.String(length=11), nullable=True),
        sa.Column("vehicle_type", sa.String(length=20), nullable=False),
        sa.Column("vehicle_type_other", sa.String(length=100), nullable=True),
        sa.Column("body_type", sa.String(length=20), nullable=False),
        sa.Column("body_type_other", sa.String(length=100), nullable=True),
        sa.Column("capacity_tons", sa.Numeric(6, 2), nullable=False),
        sa.Column("cargo_types", JSON_TYPE, nullable=False),
        sa.Column("cargo_type_other", sa.String(length=150), nullable=True),
        *_ts(),
    )
    op.create_index("ix_logistics_driver_profiles_national_code", "logistics_driver_profiles", ["national_code"])
    op.create_index("ix_logistics_driver_vehicle", "logistics_driver_profiles", ["vehicle_type", "body_type"])

    op.create_table(
        "logistics_service_areas",
        sa.Column("id", BIG, primary_key=True, autoincrement=True),
        _applicant_fk(),
        sa.Column("area_type", sa.String(length=20), nullable=False),
        sa.Column("coverage", JSON_TYPE, nullable=False),
        sa.Column("origin_countries", JSON_TYPE, nullable=False),
        sa.Column("destination_countries", JSON_TYPE, nullable=False),
        sa.Column("permits", JSON_TYPE, nullable=False),
        *_ts(),
    )
    op.create_index("ix_logistics_service_areas_area_type", "logistics_service_areas", ["area_type"])

    op.create_table(
        "logistics_files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by_user_id", BIG, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_ts(),
    )

    _seed_permissions_and_roles()


# ---------------------------------------------------------------------
# Data seed (idempotent)
# ---------------------------------------------------------------------
RESOURCES = ("company", "driver")
ACTIONS = ("create", "read", "update", "delete", "review")

# role name -> (display name, description, actions granted on BOTH resources)
ROLES = {
    "logistics_manager": ("مدیر لجستیک", "Full access to transport companies and drivers, including review.", ACTIONS),
    "logistics_operator": ("کارشناس ثبت‌نام لجستیک", "Can view, add and edit registrations; cannot delete or review.", ("read", "create", "update")),
    "logistics_viewer": ("مشاهده‌گر لجستیک", "Read-only access to transport companies and drivers.", ("read",)),
}

permissions = sa.table(
    "permissions",
    sa.column("id", sa.BigInteger), sa.column("key", sa.String), sa.column("module", sa.String),
    sa.column("resource", sa.String), sa.column("action", sa.String), sa.column("is_delegable", sa.Boolean),
    sa.column("description", sa.String), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
roles = sa.table(
    "roles",
    sa.column("id", sa.BigInteger), sa.column("name", sa.String), sa.column("display_name", sa.String),
    sa.column("description", sa.String), sa.column("is_system_role", sa.Boolean), sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
)
role_scopes = sa.table(
    "role_permission_scopes",
    sa.column("id", sa.BigInteger), sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger),
    sa.column("scope_type", sa.String), sa.column("scope_id", sa.BigInteger), sa.column("is_active", sa.Boolean),
    sa.column("granted_by_user_id", sa.BigInteger), sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def _permission_id(bind, key: str, resource: str, action: str, now) -> int:
    pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    if pid is None:
        bind.execute(permissions.insert().values(
            key=key, module="logistics", resource=resource, action=action,
            is_delegable=(action != "review"),
            description=f"{action.capitalize()} logistics {resource} records.",
            created_at=now, updated_at=now,
        ))
        pid = bind.execute(sa.select(permissions.c.id).where(permissions.c.key == key)).scalar()
    return pid


def _grant_global(bind, role_id: int, permission_id: int, now) -> None:
    row = bind.execute(sa.select(role_scopes.c.id).where(
        role_scopes.c.role_id == role_id, role_scopes.c.permission_id == permission_id,
        role_scopes.c.scope_type == "GLOBAL",
    )).first()
    if row is None:
        bind.execute(role_scopes.insert().values(
            role_id=role_id, permission_id=permission_id, scope_type="GLOBAL", scope_id=None,
            is_active=True, granted_by_user_id=None, created_at=now, updated_at=now,
        ))
    else:
        bind.execute(role_scopes.update().where(role_scopes.c.id == row[0]).values(is_active=True))


def _seed_permissions_and_roles() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()

    ids = {
        (res, act): _permission_id(bind, f"logistics.{res}.{act}", res, act, now)
        for res in RESOURCES for act in ACTIONS
    }

    admin_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    if admin_id is not None:
        for pid in ids.values():
            _grant_global(bind, admin_id, pid, now)

    for name, (display, description, actions) in ROLES.items():
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == name)).scalar()
        if role_id is None:
            bind.execute(roles.insert().values(
                name=name, display_name=display, description=description, is_system_role=True,
                is_active=True, created_at=now, updated_at=now,
            ))
            role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == name)).scalar()
        for res in RESOURCES:
            for act in actions:
                _grant_global(bind, role_id, ids[(res, act)], now)


def downgrade():
    # Tables only. Permission/role rows are intentionally kept: removing them could
    # silently strip access that was assigned to people in the meantime.
    op.drop_table("logistics_files")
    op.drop_index("ix_logistics_service_areas_area_type", table_name="logistics_service_areas")
    op.drop_table("logistics_service_areas")
    op.drop_index("ix_logistics_driver_vehicle", table_name="logistics_driver_profiles")
    op.drop_index("ix_logistics_driver_profiles_national_code", table_name="logistics_driver_profiles")
    op.drop_table("logistics_driver_profiles")
    op.drop_index("ix_logistics_company_province_city", table_name="logistics_company_profiles")
    op.drop_index("ix_logistics_company_profiles_national_id", table_name="logistics_company_profiles")
    op.drop_table("logistics_company_profiles")
    op.drop_index("ix_logistics_applicants_type_mobile", table_name="logistics_applicants")
    op.drop_index("ix_logistics_applicants_type_status", table_name="logistics_applicants")
    op.drop_table("logistics_applicants")
