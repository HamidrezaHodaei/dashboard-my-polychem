"""
Team and TeamMember models — DATABASE.md "Organizational structure > teams
/ team_members".

`manager_user_id` on Team is **informational only**, same caveat as
`Department.manager_user_id` — see AUTHORIZATION.md §2.

`TeamMember` is plain many-to-many team membership, not authorization —
"where does this employee sit," not "what can they do."
"""
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, Index, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.core.base import TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, BigIntUnsigned


class Team(TimestampMixin, SoftDeleteMixin, ActiveFlagMixin, db.Model):
    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_department_id", "department_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # Informational org-chart label only — NEVER read by the authorization
    # engine (AUTHORIZATION.md §2), same caveat as Department.manager_user_id.
    # use_alter=True: same circular-dependency rationale as
    # Department.manager_user_id (see app/core/departments/models.py).
    manager_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_teams_manager_user_id",
        ),
        nullable=True,
    )

    department: Mapped["Department"] = relationship(
        "Department", back_populates="teams"
    )
    manager: Mapped["User | None"] = relationship(
        "User", foreign_keys=[manager_user_id]
    )
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Team id={self.id} name={self.name!r}>"


class TeamMember(db.Model):
    """
    Many-to-many team membership. No created_at/updated_at/deleted_at per
    DATABASE.md — membership rows are simply added/removed, not soft-deleted.
    """

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    team_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned,
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="team_memberships")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TeamMember team_id={self.team_id} user_id={self.user_id}>"
