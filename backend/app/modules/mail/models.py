"""
Organizational correspondence (مکاتبات سازمانی) -- internal mail between platform users.

Tables
    mail_messages      one row per message (a thread = the root message + its replies, `thread_id`)
    mail_participants  one row per (message, user): the sender and every TO / CC recipient. It carries
                       that user's PRIVATE state of the message -- folder, read, starred, labels,
                       muted -- so archiving or trashing a message never affects anybody else's copy.
    mail_attachments   files uploaded for a message (stored on disk, metadata here)
    mail_unit_access   organizational units (departments) whose members may use the module; the
                       per-user / per-role switch is the ordinary permission matrix
                       (`correspondence.mail.*`), see access.py.

Nothing here owns a user, department or avatar table: people come from `users` (profile photo =
`users.avatar_data`), units from `departments` / `team_members`.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import BigIntUnsigned, TimestampMixin
from app.extensions import db

LongText = Text().with_variant(mysql.MEDIUMTEXT(), "mysql")

# Folders a participant's copy can be in.
FOLDERS = ("INBOX", "SENT", "DRAFT", "SPAM", "TRASH", "ARCHIVE")
ROLES = ("SENDER", "TO", "CC")

# Fixed label set (same idea as the reference mail app's coloured labels). The key is stored,
# the Persian title and colour live in the frontend.
LABELS = ("urgent", "work", "finance", "meeting", "info")


class MailMessage(TimestampMixin, db.Model):
    __tablename__ = "mail_messages"
    __table_args__ = (
        Index("ix_mail_messages_thread", "thread_id", "id"),
        Index("ix_mail_messages_sender", "sender_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    # Root message id of the conversation. A new conversation points at itself (set right after the
    # first flush); a reply copies the parent's thread_id.
    thread_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("mail_messages.id", ondelete="SET NULL"), nullable=True
    )
    sender_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    body: Mapped[str] = mapped_column(LongText, nullable=False, default="")
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # JSON {"to": [user ids], "cc": [user ids]} while the message is a draft. Recipients get their
    # participant rows only when it is sent, so a draft never shows up in anybody else's mailbox.
    draft_recipients: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    participants: Mapped[list["MailParticipant"]] = relationship(
        "MailParticipant", back_populates="message", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["MailAttachment"]] = relationship(
        "MailAttachment", back_populates="message", cascade="all, delete-orphan"
    )


class MailParticipant(TimestampMixin, db.Model):
    __tablename__ = "mail_participants"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_mail_participants_message_user"),
        Index("ix_mail_participants_user_folder", "user_id", "folder", "is_read"),
        Index("ix_mail_participants_message", "message_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("mail_messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # SENDER | TO | CC
    folder: Mapped[str] = mapped_column(String(10), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    labels: Mapped[str] = mapped_column(String(120), nullable=False, default="")  # comma separated keys
    # "Delete permanently" only hides the message for this user; the other participants keep theirs.
    purged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    message: Mapped[MailMessage] = relationship("MailMessage", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])


class MailAttachment(TimestampMixin, db.Model):
    __tablename__ = "mail_attachments"
    __table_args__ = (Index("ix_mail_attachments_message", "message_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid
    # NULL while the file is uploaded but not yet attached to a message (compose in progress).
    message_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("mail_messages.id", ondelete="CASCADE"), nullable=True
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    message: Mapped[MailMessage | None] = relationship("MailMessage", back_populates="attachments")


class MailUnitAccess(TimestampMixin, db.Model):
    """A department whose members (users.department_id, or a member of one of its teams) may use mail."""

    __tablename__ = "mail_unit_access"
    __table_args__ = (UniqueConstraint("department_id", name="uq_mail_unit_access_department"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    granted_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
