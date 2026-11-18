"""
Correspondence business logic. Permissions (`correspondence.mail.*`, or an enabled organizational unit)
are enforced HERE through access.require(); the routes only authenticate, so hiding a button in the UI
is never the only protection.

Privacy model: every query starts from the ACTING user's own `mail_participants` rows. A message the
user is not a participant of -- or one they permanently deleted -- does not exist for them (404), so
changing an id in the URL can never expose someone else's mail.

Mailbox folders (per user, per message): INBOX, SENT, DRAFT, SPAM, TRASH, ARCHIVE.
A conversation (thread) is the root message plus its replies; lists show one row per thread.
"""
import json
import re
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import aliased, undefer

from app.core.audit_logs.services import write_audit_log
from app.core.departments.models import Department
from app.core.users.models import User
from app.extensions import db
from app.modules.mail import access, files
from app.modules.mail.models import (
    LABELS, MailAttachment, MailMessage, MailParticipant, MailUnitAccess,
)
from app.modules.mail.schemas import ComposeIn, FlagsIn, LabelsIn, ReplyIn, UnitAccessIn
from app.modules.notifications import services as notifications
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError

MODULE = "correspondence"
FOLDER_BY_SLUG = {
    "inbox": "INBOX", "sent": "SENT", "drafts": "DRAFT", "spam": "SPAM", "trash": "TRASH", "archive": "ARCHIVE",
}
SLUG_BY_FOLDER = {v: k for k, v in FOLDER_BY_SLUG.items()}
LABEL_VIEW_FOLDERS = ("INBOX", "SENT", "ARCHIVE")
NO_SUBJECT = "(بدون موضوع)"
PREVIEW_LEN = 140


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def _thread_key():
    """The conversation a message belongs to (a draft without a thread is its own conversation)."""
    return func.coalesce(MailMessage.thread_id, MailMessage.id)


def _label_list(raw: str | None) -> list[str]:
    return [x for x in (raw or "").split(",") if x in LABELS]


# ── people ───────────────────────────────────────────────────────────
def _people(ids: set[int]) -> dict[int, dict]:
    """id -> public card of the user. Name, e-mail, department and the profile photo all come straight
    from the users table (`users.avatar_data`, the same photo the account / header use)."""
    if not ids:
        return {}
    rows = (
        db.session.query(User, Department.name)
        .outerjoin(Department, Department.id == User.department_id)
        .options(undefer(User.avatar_data))
        .filter(User.id.in_(ids))
        .all()
    )
    return {
        u.id: {
            "id": u.id, "full_name": u.full_name, "username": u.username, "email": u.email,
            "department": dept, "avatar": u.avatar_data or None,
        }
        for u, dept in rows
    }


def _recipient_ids(message: MailMessage, role: str) -> list[int]:
    return [p.user_id for p in sorted(message.participants, key=lambda p: p.id) if p.role == role]


def _draft_ids(message: MailMessage) -> tuple[list[int], list[int]]:
    try:
        data = json.loads(message.draft_recipients or "{}")
    except ValueError:
        data = {}
    return [int(i) for i in data.get("to", [])], [int(i) for i in data.get("cc", [])]


# ── participation lookups ────────────────────────────────────────────
def _mine(actor: User):
    return db.session.query(MailParticipant).filter(
        MailParticipant.user_id == actor.id, MailParticipant.purged_at.is_(None)
    )


def _own_participation(actor: User, message_id: int) -> tuple[MailMessage, MailParticipant]:
    row = (
        _mine(actor).filter(MailParticipant.message_id == message_id).first()
    )
    if row is None:
        raise NotFoundError("Message was not found.")
    return row.message, row


def _folder_class(folder: str) -> str:
    """Rows of one conversation live in different folders (a sent reply, a received message, a trashed
    one...). The mailbox shows a conversation per *class*: the everyday folders together, and spam, trash
    and drafts each on their own -- so trashing a conversation never drags a message from the inbox of
    another view along, and a draft reply is never part of somebody's inbox thread."""
    return "NORMAL" if folder in ("INBOX", "SENT", "ARCHIVE") else folder


def _thread_rows(actor: User, message_id: int) -> list[MailParticipant]:
    """The acting user's (non-purged) rows of the conversation of `message_id`, restricted to the class of
    the folder that message is in. A draft is always a conversation of one."""
    message, anchor = _own_participation(actor, message_id)
    if anchor.folder == "DRAFT":
        return [anchor]
    key = message.thread_id or message.id
    klass = _folder_class(anchor.folder)
    rows = (
        _mine(actor)
        .join(MailMessage, MailMessage.id == MailParticipant.message_id)
        .filter(_thread_key() == key)
        .order_by(MailMessage.id)
        .all()
    )
    return [p for p in rows if _folder_class(p.folder) == klass]


# ── recipients ───────────────────────────────────────────────────────
def _fa_normalize(value: str) -> str:
    return (value or "").replace("ي", "ی").replace("ك", "ک").strip()


def _norm_col(column):
    return func.replace(func.replace(column, "ي", "ی"), "ك", "ک")


def search_recipients(actor: User, q: str | None, *, limit: int = 20, exclude: list[int] | None = None) -> list[dict]:
    """People the actor may write to. Matches first name, last name, username and e-mail (every word of
    the query must match one of them). Only active users who can themselves open correspondence."""
    access.require(actor, "create")
    limit = max(1, min(int(limit), 50))
    query = db.session.query(User).options(undefer(User.avatar_data)).filter(
        User.is_active.is_(True), User.deleted_at.is_(None), User.id != actor.id,
    )
    if exclude:
        query = query.filter(User.id.notin_(exclude))
    for token in _fa_normalize(q or "").lower().split()[:6]:
        like = f"%{token.replace('%', '').replace('_', '')}%"
        query = query.filter(or_(
            func.lower(_norm_col(User.full_name)).like(like),
            func.lower(User.username).like(like),
            func.lower(User.email).like(like),
        ))
    out: list[dict] = []
    # users without mail access are skipped, so scan a few more rows than we return
    for user in query.order_by(User.full_name, User.id).limit(limit * 3).all():
        if access.can(user, "read"):
            out.append(user)
        if len(out) >= limit:
            break
    people = _people({u.id for u in out})
    cards = []
    for u in out:
        card = dict(people[u.id])
        parts = (u.full_name or "").split(None, 1)
        card["first_name"] = parts[0] if parts else ""
        card["last_name"] = parts[1] if len(parts) > 1 else ""
        cards.append(card)
    return cards


def _validate_recipients(actor: User, ids: list[int], *, strict: bool) -> list[User]:
    """Resolve ids to users. strict (sending): each one must be an active user with mail access, and
    not the sender. Drafts only need the users to exist."""
    if not ids:
        return []
    users = {u.id: u for u in db.session.query(User).filter(User.id.in_(ids)).all()}
    out: list[User] = []
    for uid in ids:
        user = users.get(uid)
        if user is None or user.deleted_at is not None or not user.is_active:
            raise InvalidInputError("یکی از گیرندگان یافت نشد یا غیرفعال است.", "to")
        if strict:
            if user.id == actor.id:
                raise InvalidInputError("نمی‌توانید برای خودتان نامه ارسال کنید.", "to")
            if not access.can(user, "read"):
                raise InvalidInputError(f"«{user.full_name}» به بخش مکاتبات دسترسی ندارد.", "to")
        out.append(user)
    return out


# ── attachments ──────────────────────────────────────────────────────
def _readable_message_ids(actor: User, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    rows = (
        _mine(actor).join(MailMessage, MailMessage.id == MailParticipant.message_id)
        .filter(MailParticipant.message_id.in_(ids), MailMessage.is_draft.is_(False))
        .with_entities(MailParticipant.message_id).all()
    )
    return {int(r[0]) for r in rows}


def _sync_attachments(actor: User, message: MailMessage, attachment_ids: list[str]) -> list[str]:
    """Make the message's attachments exactly `attachment_ids`.
    * a file already on this message stays;
    * a file the actor just uploaded (not attached anywhere) is adopted;
    * a file of another message the actor can read (a forward) is copied -- same stored file, new row.
    Anything else is rejected, so nobody can attach somebody else's upload by guessing an id.
    Returns the stored names of files dropped from the message; the caller deletes them from disk AFTER
    the commit (so a failed request never loses a file)."""
    if len(attachment_ids) > files.MAX_FILES_PER_MESSAGE:
        raise InvalidInputError(f"حداکثر {files.MAX_FILES_PER_MESSAGE} فایل پیوست مجاز است.", "attachments")
    current = {a.id: a for a in message.attachments}
    wanted: list[MailAttachment] = []
    new_rows: list[MailAttachment] = []
    for fid in attachment_ids:
        if fid in current:
            wanted.append(current[fid])
            continue
        row = db.session.get(MailAttachment, fid)
        if row is None:
            raise InvalidInputError("فایل پیوست یافت نشد.", "attachments")
        if row.message_id is None:
            if row.uploaded_by_user_id != actor.id:
                raise InvalidInputError("فایل پیوست یافت نشد.", "attachments")
            wanted.append(row)
            new_rows.append(row)
        else:
            if not _readable_message_ids(actor, {row.message_id}):
                raise InvalidInputError("فایل پیوست یافت نشد.", "attachments")
            import uuid

            copy = MailAttachment(
                id=str(uuid.uuid4()), uploaded_by_user_id=actor.id, original_name=row.original_name,
                stored_name=row.stored_name, content_type=row.content_type, size=row.size,
            )
            wanted.append(copy)
            new_rows.append(copy)
    total = sum(a.size for a in wanted)
    if total > files.MAX_TOTAL_MB_PER_MESSAGE * 1024 * 1024:
        raise InvalidInputError(f"مجموع حجم پیوست‌ها نباید از {files.MAX_TOTAL_MB_PER_MESSAGE} مگابایت بیشتر شود.", "attachments")
    keep = {a.id for a in wanted}
    removed = [a for a in message.attachments if a.id not in keep]
    for a in removed:
        message.attachments.remove(a)
        db.session.delete(a)
    for a in new_rows:
        a.message_id = message.id
        message.attachments.append(a)
    db.session.flush()
    return [a.stored_name for a in removed]


def _cleanup_files(stored_names: list[str]) -> None:
    for name in stored_names:
        files.remove_from_disk_if_unused(name)


# ── dumping ──────────────────────────────────────────────────────────
def _preview(body: str) -> str:
    return re.sub(r"\s+", " ", body or "").strip()[:PREVIEW_LEN]


def _dump_message(message: MailMessage, part: MailParticipant | None, actor: User) -> dict:
    if message.is_draft:
        to_ids, cc_ids = _draft_ids(message)
    else:
        to_ids, cc_ids = _recipient_ids(message, "TO"), _recipient_ids(message, "CC")
    return {
        "id": message.id, "thread_id": message.thread_id or message.id, "parent_id": message.parent_id,
        "subject": message.subject, "body": message.body, "is_draft": message.is_draft,
        "sender_id": message.sender_id, "to": to_ids, "cc": cc_ids,
        "sent_at": _iso(message.sent_at), "created_at": _iso(message.created_at), "updated_at": _iso(message.updated_at),
        "is_mine": message.sender_id == actor.id,
        "attachments": [files.file_ref(a) for a in sorted(message.attachments, key=lambda a: a.created_at)],
        "folder": SLUG_BY_FOLDER.get(part.folder) if part else None,
        "is_read": part.is_read if part else True, "is_starred": part.is_starred if part else False,
    }


def _people_of(messages: list[MailMessage]) -> set[int]:
    ids: set[int] = set()
    for m in messages:
        ids.add(m.sender_id)
        if m.is_draft:
            to, cc = _draft_ids(m)
            ids.update(to)
            ids.update(cc)
        else:
            ids.update(p.user_id for p in m.participants)
    return ids


# ── mailbox list ─────────────────────────────────────────────────────
def _base_filters(actor: User, folder: str | None, label: str | None, unread: bool, starred: bool):
    conds = [MailParticipant.user_id == actor.id, MailParticipant.purged_at.is_(None)]
    if folder:
        conds.append(MailParticipant.folder == folder)
    else:
        conds.append(MailParticipant.folder.in_(LABEL_VIEW_FOLDERS) if label else MailParticipant.folder != "TRASH")
    if label:
        conds.append(or_(
            MailParticipant.labels == label, MailParticipant.labels.like(f"{label},%"),
            MailParticipant.labels.like(f"%,{label}"), MailParticipant.labels.like(f"%,{label},%"),
        ))
    if unread:
        conds.append(MailParticipant.is_read.is_(False))
    if starred:
        conds.append(MailParticipant.is_starred.is_(True))
    return conds


def list_threads(
    actor: User, *, folder_slug: str | None = "inbox", label: str | None = None, q: str | None = None,
    unread: bool = False, starred: bool = False, sort: str = "newest", page: int = 1, per_page: int = 30,
) -> tuple[list[dict], int, dict]:
    access.require(actor, "read")
    folder = None
    if folder_slug:
        folder = FOLDER_BY_SLUG.get(folder_slug)
        if folder is None:
            raise InvalidInputError("پوشهٔ نامعتبر است.", "folder")
    if label and label not in LABELS:
        raise InvalidInputError("برچسب نامعتبر است.", "label")

    Sender = aliased(User)
    conds = _base_filters(actor, folder, label, unread, starred)
    query = (
        db.session.query(func.max(MailMessage.id).label("mid"))
        .select_from(MailParticipant)
        .join(MailMessage, MailMessage.id == MailParticipant.message_id)
        .join(Sender, Sender.id == MailMessage.sender_id)
        .filter(*conds)
    )
    for token in _fa_normalize(q or "").lower().split()[:6]:
        like = f"%{token.replace('%', '').replace('_', '')}%"
        query = query.filter(or_(
            func.lower(_norm_col(MailMessage.subject)).like(like),
            func.lower(_norm_col(MailMessage.body)).like(like),
            func.lower(_norm_col(Sender.full_name)).like(like),
            func.lower(Sender.email).like(like),
        ))
    if folder == "DRAFT":
        query = query.group_by(MailMessage.id)  # drafts are listed one by one
    else:
        query = query.group_by(_thread_key())
    latest_ids = [int(r[0]) for r in query.all()]
    total = len(latest_ids)

    order = MailMessage.id.asc() if sort == "oldest" else MailMessage.id.desc()
    page_ids = [
        int(r[0]) for r in db.session.query(MailMessage.id).filter(MailMessage.id.in_(latest_ids or [0]))
        .order_by(order).offset((page - 1) * per_page).limit(per_page).all()
    ]
    messages = {m.id: m for m in db.session.query(MailMessage).filter(MailMessage.id.in_(page_ids or [0])).all()}
    my_rows = {
        p.message_id: p for p in _mine(actor).filter(MailParticipant.message_id.in_(page_ids or [0])).all()
    }

    # thread-level numbers (how many messages the user sees, any unread, any star) for the page
    keys = {m.thread_id or m.id for m in messages.values()}
    stats: dict[int, dict] = {}
    if keys:
        klass_filter = (
            MailParticipant.folder == folder if folder in ("TRASH", "SPAM", "DRAFT")
            else MailParticipant.folder.in_(("INBOX", "SENT", "ARCHIVE"))
        )
        rows = (
            _mine(actor).join(MailMessage, MailMessage.id == MailParticipant.message_id)
            .filter(_thread_key().in_(keys), klass_filter)
            .with_entities(_thread_key(), MailParticipant.is_read, MailParticipant.is_starred, MailParticipant.labels)
            .all()
        )
        for key, is_read, is_starred, labels in rows:
            s = stats.setdefault(int(key), {"count": 0, "unread": 0, "starred": False, "labels": set()})
            s["count"] += 1
            s["unread"] += 0 if is_read else 1
            s["starred"] = s["starred"] or bool(is_starred)
            s["labels"].update(_label_list(labels))

    ordered = [messages[i] for i in page_ids if i in messages]
    people = _people(_people_of(ordered))
    items = []
    for m in ordered:
        part = my_rows.get(m.id)
        s = stats.get(m.thread_id or m.id, {"count": 1, "unread": 0, "starred": False, "labels": set()})
        item = _dump_message(m, part, actor)
        item.pop("body")
        item.update({
            "preview": _preview(m.body), "thread_count": max(s["count"], 1),
            "is_read": s["unread"] == 0, "is_starred": s["starred"] if folder != "DRAFT" else item["is_starred"],
            "labels": sorted(s["labels"], key=LABELS.index) if folder != "DRAFT" else _label_list(part.labels if part else ""),
            "has_attachments": bool(m.attachments),
        })
        items.append(item)
    return items, total, people


def counters(actor: User) -> dict:
    """Thread counts for the folder / label sidebar: inbox shows its unread number, the other folders
    their size (like the reference app)."""
    access.require(actor, "read")
    rows = (
        _mine(actor).join(MailMessage, MailMessage.id == MailParticipant.message_id)
        .with_entities(_thread_key(), MailMessage.id, MailParticipant.folder, MailParticipant.is_read, MailParticipant.labels)
        .all()
    )
    folders = {slug: {"total": set(), "unread": set()} for slug in FOLDER_BY_SLUG}
    labels = {label: set() for label in LABELS}
    for key, mid, folder, is_read, label_raw in rows:
        slug = SLUG_BY_FOLDER[folder]
        ident = mid if folder == "DRAFT" else key
        folders[slug]["total"].add(ident)
        if not is_read:
            folders[slug]["unread"].add(ident)
        if folder in LABEL_VIEW_FOLDERS:
            for label in _label_list(label_raw):
                labels[label].add(key)
    return {
        "folders": {s: {"total": len(v["total"]), "unread": len(v["unread"])} for s, v in folders.items()},
        "labels": {k: len(v) for k, v in labels.items()},
    }


def meta(actor: User) -> dict:
    return {
        "access": access.access_summary(actor),
        "can_manage_access": access.can_manage_access(actor),
        "labels": list(LABELS),
        "limits": {
            "max_files": files.MAX_FILES_PER_MESSAGE,
            "max_file_mb": files.max_file_bytes() // (1024 * 1024),
            "max_total_mb": files.MAX_TOTAL_MB_PER_MESSAGE,
            "allowed_extensions": sorted(files.ALLOWED_EXTENSIONS),
        },
    }


# ── one conversation ─────────────────────────────────────────────────
def get_thread(actor: User, message_id: int) -> dict:
    access.require(actor, "read")
    rows = _thread_rows(actor, message_id)
    messages = [p.message for p in rows]
    by_msg = {p.message_id: p for p in rows}
    people = _people(_people_of(messages))
    labels: set[str] = set()
    for p in rows:
        labels.update(_label_list(p.labels))
    anchor = by_msg.get(message_id) or rows[-1]
    return {
        "thread_id": anchor.message.thread_id or anchor.message.id,
        "subject": messages[-1].subject,
        "folder": SLUG_BY_FOLDER.get(anchor.folder),
        "is_muted": any(p.is_muted for p in rows),
        "is_starred": any(p.is_starred for p in rows),
        "labels": sorted(labels, key=LABELS.index),
        "messages": [_dump_message(m, by_msg[m.id], actor) for m in messages],
        "people": people,
    }


# ── composing / sending ──────────────────────────────────────────────
def _own_draft(actor: User, draft_id: int) -> MailMessage:
    message = db.session.get(MailMessage, draft_id)
    if message is None or message.sender_id != actor.id or not message.is_draft:
        raise NotFoundError("Draft was not found.")
    row = _mine(actor).filter(MailParticipant.message_id == draft_id).first()
    if row is None:
        raise NotFoundError("Draft was not found.")
    return message


def _parent_for(actor: User, parent_id: int | None) -> MailMessage | None:
    if parent_id is None:
        return None
    parent, _ = _own_participation(actor, parent_id)
    if parent.is_draft:
        raise InvalidInputError("به پیش‌نویس نمی‌توان پاسخ داد.", "parent_id")
    return parent


def _ensure_sender_row(actor: User, message: MailMessage, folder: str) -> MailParticipant:
    row = next((p for p in message.participants if p.user_id == actor.id), None)
    if row is None:
        row = MailParticipant(message_id=message.id, user_id=actor.id, role="SENDER", folder=folder, is_read=True)
        db.session.add(row)
        message.participants.append(row)
    else:
        row.folder = folder
        row.is_read = True
    return row


def save_draft(actor: User, payload: ComposeIn, draft_id: int | None = None, ip_address: str | None = None) -> dict:
    access.require(actor, "create")
    parent = _parent_for(actor, payload.parent_id)
    _validate_recipients(actor, payload.to + payload.cc, strict=False)
    if draft_id is None:
        message = MailMessage(sender_id=actor.id, is_draft=True, subject="", body="")
        db.session.add(message)
        db.session.flush()
        message.thread_id = parent.thread_id or parent.id if parent else message.id
        message.parent_id = parent.id if parent else None
        _ensure_sender_row(actor, message, "DRAFT")
    else:
        message = _own_draft(actor, draft_id)
    message.subject = payload.subject
    message.body = payload.body
    cc = [i for i in payload.cc if i not in payload.to]
    message.draft_recipients = json.dumps({"to": payload.to, "cc": cc})
    dropped = _sync_attachments(actor, message, payload.attachment_ids)
    db.session.commit()
    _cleanup_files(dropped)
    part = next(p for p in message.participants if p.user_id == actor.id)
    return {"message": _dump_message(message, part, actor), "people": _people(_people_of([message]))}


def _finalize_send(actor: User, message: MailMessage, to: list[int], cc: list[int], ip_address: str | None) -> None:
    to_users = _validate_recipients(actor, to, strict=True)
    cc_users = _validate_recipients(actor, [i for i in cc if i not in to], strict=True)
    if not to_users and not cc_users:
        raise InvalidInputError("حداقل یک گیرنده انتخاب کنید.", "to")
    if not (message.body or "").strip() and not message.attachments:
        raise InvalidInputError("متن نامه یا حداقل یک پیوست لازم است.", "body")
    if not message.subject:
        message.subject = NO_SUBJECT
    message.is_draft = False
    message.sent_at = _now()
    message.draft_recipients = None
    if message.thread_id is None:
        message.thread_id = message.id
    _ensure_sender_row(actor, message, "SENT")
    existing = {p.user_id for p in message.participants}
    muted_users = {
        int(r[0]) for r in db.session.query(MailParticipant.user_id)
        .join(MailMessage, MailMessage.id == MailParticipant.message_id)
        .filter(_thread_key() == message.thread_id, MailParticipant.is_muted.is_(True)).all()
    }
    for role, users in (("TO", to_users), ("CC", cc_users)):
        for user in users:
            if user.id in existing:
                continue
            db.session.add(MailParticipant(
                message_id=message.id, user_id=user.id, role=role, folder="INBOX", is_read=False,
                is_muted=user.id in muted_users,
            ))
            existing.add(user.id)
            if user.id not in muted_users:
                notifications.notify(
                    user.id, "MAIL", f"نامهٔ جدید از {actor.full_name}", message.subject,
                    link=f"/mail?thread={message.id}", dedupe_key=f"mail:{message.id}",
                )
    write_audit_log(
        user_id=actor.id, action="send", module=MODULE, entity_type="mail_message", entity_id=message.id,
        metadata={"to": len(to_users), "cc": len(cc_users), "attachments": len(message.attachments)},
        ip_address=ip_address,
    )


def send(actor: User, payload: ComposeIn, draft_id: int | None = None, ip_address: str | None = None) -> dict:
    """Send a new message (or a draft). Replies pass `parent_id`."""
    access.require(actor, "create")
    parent = _parent_for(actor, payload.parent_id)
    to, cc = payload.to, [i for i in payload.cc if i not in payload.to]
    if draft_id is None:
        message = MailMessage(sender_id=actor.id, is_draft=True, subject=payload.subject, body=payload.body)
        db.session.add(message)
        db.session.flush()
        message.thread_id = parent.thread_id or parent.id if parent else message.id
        message.parent_id = parent.id if parent else None
        _ensure_sender_row(actor, message, "DRAFT")
    else:
        message = _own_draft(actor, draft_id)
        message.subject, message.body = payload.subject, payload.body
        if payload.parent_id is not None:
            message.parent_id = parent.id
            message.thread_id = parent.thread_id or parent.id
    dropped = _sync_attachments(actor, message, payload.attachment_ids)
    _finalize_send(actor, message, to, cc, ip_address)
    db.session.commit()
    _cleanup_files(dropped)
    part = next(p for p in message.participants if p.user_id == actor.id)
    return {"message": _dump_message(message, part, actor), "people": _people(_people_of([message]))}


def reply(actor: User, message_id: int, payload: ReplyIn, ip_address: str | None = None) -> dict:
    access.require(actor, "create")
    parent, _ = _own_participation(actor, message_id)
    if parent.is_draft:
        raise InvalidInputError("به پیش‌نویس نمی‌توان پاسخ داد.", "parent_id")
    if parent.sender_id == actor.id:
        auto = _recipient_ids(parent, "TO")  # answering my own message goes to the same people
        auto_cc = _recipient_ids(parent, "CC") if payload.reply_all else []
    else:
        auto = [parent.sender_id]
        auto_cc = (
            [i for i in _recipient_ids(parent, "TO") + _recipient_ids(parent, "CC") if i != actor.id and i != parent.sender_id]
            if payload.reply_all else []
        )
    # automatic recipients that have since been deactivated / lost access are simply left out
    def usable(ids: list[int]) -> list[int]:
        users = {u.id: u for u in db.session.query(User).filter(User.id.in_(ids or [0])).all()}
        return [i for i in ids if i in users and users[i].is_active and users[i].deleted_at is None
                and i != actor.id and access.can(users[i], "read")]
    to = usable(auto) + [i for i in payload.to if i not in auto]
    cc = usable(auto_cc) + [i for i in payload.cc if i not in to]
    subject = parent.subject if re.match(r"^(re|پاسخ)\s*:", parent.subject, re.I) else f"Re: {parent.subject}"
    compose = ComposeIn(
        to=to, cc=cc, subject=subject, body=payload.body, attachment_ids=payload.attachment_ids, parent_id=parent.id,
    )
    return send(actor, compose, None, ip_address)


def discard_draft(actor: User, draft_id: int, ip_address: str | None = None) -> None:
    access.require(actor, "create")  # a draft is the author's own work in progress
    message = _own_draft(actor, draft_id)
    stored = [a.stored_name for a in message.attachments]
    db.session.delete(message)
    db.session.flush()
    for name in stored:
        files.remove_from_disk_if_unused(name)
    db.session.commit()


# ── per-user state ───────────────────────────────────────────────────
def move_thread(actor: User, message_id: int, slug: str, ip_address: str | None = None) -> dict:
    """Move the actor's copy of the whole conversation. Trash needs `delete`, everything else `update`.
    "inbox" also means "restore": received messages go back to the inbox, sent ones to Sent."""
    access.require(actor, "delete" if slug == "trash" else "update")
    rows = _thread_rows(actor, message_id)
    for p in rows:
        if p.message.is_draft:
            p.folder = "TRASH" if slug == "trash" else "DRAFT"  # a draft can only be trashed / restored
        elif slug == "inbox":
            p.folder = "SENT" if p.role == "SENDER" else "INBOX"
        else:
            p.folder = FOLDER_BY_SLUG[slug]
    db.session.commit()
    return get_thread(actor, message_id)


def delete_thread_permanently(actor: User, message_id: int, ip_address: str | None = None) -> None:
    """Remove the conversation from the actor's mailbox for good. Only from trash / spam; the other
    participants keep their copies."""
    access.require(actor, "delete")
    rows = _thread_rows(actor, message_id)
    if any(p.folder not in ("TRASH", "SPAM") for p in rows):
        raise ConflictError("فقط نامه‌های سطل زباله یا هرزنامه را می‌توان برای همیشه حذف کرد.")
    now = _now()
    for p in rows:
        p.purged_at = now
    write_audit_log(
        user_id=actor.id, action="purge", module=MODULE, entity_type="mail_message", entity_id=message_id,
        ip_address=ip_address,
    )
    db.session.commit()


def set_flags(actor: User, message_id: int, payload: FlagsIn) -> dict:
    access.require(actor, "update")
    rows = _thread_rows(actor, message_id)
    now = _now()
    for p in rows:
        if payload.is_read is not None:
            p.is_read = payload.is_read
            p.read_at = now if payload.is_read else None
        if payload.is_starred is not None:
            p.is_starred = payload.is_starred
        if payload.is_muted is not None:
            p.is_muted = payload.is_muted
    db.session.commit()
    return get_thread(actor, message_id)


def set_labels(actor: User, message_id: int, payload: LabelsIn) -> dict:
    access.require(actor, "update")
    rows = _thread_rows(actor, message_id)
    value = ",".join(payload.labels)
    for p in rows:
        p.labels = value
    db.session.commit()
    return get_thread(actor, message_id)


# ── attachments ──────────────────────────────────────────────────────
def upload_attachment(actor: User, file) -> dict:
    access.require(actor, "create")
    row = files.save_upload(file, uploaded_by_user_id=actor.id)
    return files.file_ref(row)


def download_attachment(actor: User, file_id: str) -> MailAttachment:
    access.require(actor, "read")
    row = files.get_or_404(file_id)
    if row.message_id is None:
        if row.uploaded_by_user_id != actor.id:
            raise NotFoundError("File was not found.")
        return row
    if not db.session.query(MailParticipant.id).filter(
        MailParticipant.message_id == row.message_id, MailParticipant.user_id == actor.id,
        MailParticipant.purged_at.is_(None),
    ).first():
        raise NotFoundError("File was not found.")
    return row


def delete_attachment(actor: User, file_id: str) -> None:
    """Remove an upload that is not part of a sent message (an orphan, or a file on the actor's draft)."""
    access.require(actor, "create")
    row = files.get_or_404(file_id)
    if row.message_id is None:
        if row.uploaded_by_user_id != actor.id:
            raise NotFoundError("File was not found.")
    else:
        message = db.session.get(MailMessage, row.message_id)
        if message is None or not message.is_draft or message.sender_id != actor.id:
            raise ConflictError("پیوست نامهٔ ارسال‌شده قابل حذف نیست.")
    stored = row.stored_name
    db.session.delete(row)
    db.session.flush()
    files.remove_from_disk_if_unused(stored)
    db.session.commit()


# ── which units may use mail (admin) ─────────────────────────────────
def list_units(actor: User) -> list[dict]:
    access.require_manage_access(actor)
    enabled = access.enabled_unit_ids()
    counts = dict(
        db.session.query(User.department_id, func.count(User.id))
        .filter(User.deleted_at.is_(None), User.is_active.is_(True), User.department_id.isnot(None))
        .group_by(User.department_id).all()
    )
    depts = db.session.query(Department).filter(Department.deleted_at.is_(None)).order_by(Department.name).all()
    return [
        {"id": d.id, "name": d.name, "enabled": d.id in enabled, "member_count": int(counts.get(d.id, 0))}
        for d in depts
    ]


def set_units(actor: User, payload: UnitAccessIn, ip_address: str | None = None) -> list[dict]:
    access.require_manage_access(actor)
    valid = {
        int(r[0]) for r in db.session.query(Department.id)
        .filter(Department.id.in_(payload.department_ids or [0]), Department.deleted_at.is_(None)).all()
    }
    if len(valid) != len(payload.department_ids):
        raise InvalidInputError("یکی از واحدهای انتخاب‌شده یافت نشد.", "department_ids")
    current = {row.department_id: row for row in db.session.query(MailUnitAccess).all()}
    for dept_id, row in current.items():
        if dept_id not in valid:
            db.session.delete(row)
    for dept_id in valid:
        if dept_id not in current:
            db.session.add(MailUnitAccess(department_id=dept_id, granted_by_user_id=actor.id))
    write_audit_log(
        user_id=actor.id, action="set_unit_access", module=MODULE, entity_type="mail_unit_access",
        metadata={"department_ids": sorted(valid)}, ip_address=ip_address,
    )
    db.session.commit()
    return list_units(actor)
