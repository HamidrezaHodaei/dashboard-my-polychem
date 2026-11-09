"""
Shared model mixins for the core platform schema (Phase 1).

Every core/RBAC table follows the same conventions documented in
DATABASE.md's "Conventions" section:
    - PK: BIGINT UNSIGNED AUTO_INCREMENT
    - created_at / updated_at on all tables
    - deleted_at (soft delete) on entities with audit/history value
    - is_active on users, roles, organizations, departments, teams

These mixins are plain Python mixins (not declarative bases) — they're
combined with app.extensions.db.Model in each model class, e.g.:

    class Organization(TimestampMixin, SoftDeleteMixin, db.Model):
        ...
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Boolean, BigInteger, Integer
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# DATABASE.md: "PK: id BIGINT UNSIGNED AUTO_INCREMENT" and every FK that
# points at one of those PKs is the same underlying type. Plain
# `Mapped[int]` alone maps to a 32-bit INTEGER by default, which is NOT
# what the schema calls for — this variant type renders BIGINT UNSIGNED on
# MySQL specifically (via with_variant).
#
# On SQLite it must render as a *literal* `INTEGER` column type, not a
# generic BigInteger ("BIGINT"). SQLite only aliases a column to its
# internal rowid (and therefore auto-generates the value on insert) when
# the sole primary-key column's declared type is exactly "INTEGER" — see
# https://www.sqlite.org/lang_createtable.html#rowid . `BigInteger` has
# INTEGER *affinity* in SQLite but is not the literal "INTEGER" type, so it
# never gets the rowid alias/autoincrement behavior: SQLite then expects an
# explicit id on every insert, which is what produced the
# `NOT NULL constraint failed: <table>.id` errors on Phase 1 tests. Adding
# the "sqlite" variant below fixes that for SQLite while leaving the MySQL
# variant (BIGINT UNSIGNED AUTO_INCREMENT) completely untouched. Applying
# the same variant to FK columns too is harmless on SQLite (its dynamic
# typing doesn't enforce column width) and keeps id/FK types consistent.
# Use this type — not bare BigInteger/Integer — for every id column and
# every FK column that references one.
BigIntUnsigned = (
    BigInteger()
    .with_variant(mysql.BIGINT(unsigned=True), "mysql")
    .with_variant(Integer, "sqlite")
)


class TimestampMixin:
    """created_at / updated_at, present on every core/RBAC table."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SoftDeleteMixin:
    """
    deleted_at — soft delete for entities with audit/history value
    (organizations, departments, teams, users, roles, tasks, ...).

    Rows are never physically deleted by default; a non-NULL deleted_at
    marks a row as retired without losing its history or breaking FKs
    held by audit_logs / delegations / grant tables that reference it.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )


class ActiveFlagMixin:
    """is_active — present on users, roles, organizations, departments, teams."""

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
