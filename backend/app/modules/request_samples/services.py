"""
Request Sample business logic. Permissions are `crm.request_sample.<action>` and are enforced HERE
(the routes only authenticate), so hiding a button in the UI is never the only protection:

    read create update delete                      the usual four
    approve reject                                 manager decisions (never on one's own request)
    dispatch                                       record shipments
    follow_up                                      record / edit routine follow-ups
    feedback                                       record the customer's FINAL feedback
    convert                                        turn an accepted sample into sales
    export                                         Excel / Word of the list

Workflow (status values in models.SampleStatus):

    DRAFT --submit--> PENDING_APPROVAL --approve--> APPROVED --dispatch--> DISPATCHED / AWAITING_FEEDBACK
                          |  \\--reject--> REJECTED        (ON_HOLD <-> back to PENDING_APPROVAL)
    AWAITING_FEEDBACK --final feedback ACCEPTED--> complete / convert  (REJECTED feedback closes as COMPLETED)

Every change appends a row to `request_sample_events` (who / when / from -> to / note).
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, exists, or_

from app.core import request_ops
from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.crm.models import CrmSale
from app.modules.crm.services import _customer_text_match
from app.modules.customers.models import Customer, CustomerOptionItem, OptionKind
from app.modules.customers.services import _option_dict
from app.modules.notifications import services as notifications
from app.modules.request_samples import files, reminders
from app.modules.request_samples.models import (
    TERMINAL, RequestSample, RequestSampleDispatch, RequestSampleEvent, RequestSampleFile,
    RequestSampleFollowUp, RequestSampleItem, SampleStatus,
)
from app.modules.request_samples.schemas import (
    DeliveryIn, DispatchIn, FeedbackIn, FollowUpIn, RequestIn, TransitionIn,
)
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.utils.jalali import format_jalali, tehran_today, to_jalali, to_tehran

JALALI_MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)

MODULE = "crm"
ENTITY = "request_sample"
S = SampleStatus
EDITABLE_BY_CREATOR = (S.DRAFT.value, S.ON_HOLD.value)
# follow-ups and the final feedback belong to the phase AFTER the customer received the sample
FOLLOWUP_OPEN = (S.AWAITING_FEEDBACK.value,)
FEEDBACK_OPEN = (S.AWAITING_FEEDBACK.value, S.COMPLETED.value)
DISPATCH_OPEN = (S.APPROVED.value, S.DISPATCHED.value, S.AWAITING_FEEDBACK.value)
KG_PER = {"kg": 1.0, "g": 0.001, "ton": 1000.0}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def link_for(req: RequestSample) -> str:
    return f"/crm/request-samples/{req.id}"


# ── permissions ───────────────────────────────────────────────────────
def _can(actor: User, action: str) -> bool:
    return has_permission(actor, f"crm.request_sample.{action}", None, None)


def _require(actor: User, action: str) -> None:
    if not _can(actor, action):
        raise PermissionDeniedError(
            "permission_denied", f"Missing permission 'crm.request_sample.{action}' for this action."
        )


def _is_creator(actor: User, req: RequestSample) -> bool:
    return req.created_by_user_id == actor.id


def _is_own(actor: User, req: RequestSample) -> bool:
    return _is_creator(actor, req) or req.sales_rep_user_id == actor.id


def can_edit(actor: User, req: RequestSample) -> bool:
    if req.status in EDITABLE_BY_CREATOR:
        return _is_creator(actor, req) or _can(actor, "update")
    if req.status == S.PENDING_APPROVAL.value:
        return _can(actor, "update") and not _is_creator(actor, req)
    return False


def viewer_flags(actor: User, req: RequestSample) -> dict:
    """What THIS user may do with THIS request right now -- the UI draws buttons from it."""
    st = req.status
    own = _is_own(actor, req)
    decide = st in (S.PENDING_APPROVAL.value, S.ON_HOLD.value) and not _is_creator(actor, req)
    return {
        "can_edit": can_edit(actor, req),
        "can_submit": st == S.DRAFT.value and (_is_creator(actor, req) or _can(actor, "update")) and _can(actor, "create"),
        "can_approve": decide and _can(actor, "approve"),
        "can_reject": decide and _can(actor, "reject"),
        "can_hold": st in (S.PENDING_APPROVAL.value, S.APPROVED.value) and _can(actor, "approve") and not _is_creator(actor, req),
        "can_resume": st == S.ON_HOLD.value and _can(actor, "approve"),
        "can_dispatch": st in DISPATCH_OPEN and _can(actor, "dispatch"),
        "can_confirm_delivery": st == S.DISPATCHED.value and (own or any(_can(actor, a) for a in ("dispatch", "follow_up"))),
        "can_follow_up": st in FOLLOWUP_OPEN and _can(actor, "follow_up"),
        "can_feedback": st in FEEDBACK_OPEN and _can(actor, "feedback"),
        "can_complete": st == S.AWAITING_FEEDBACK.value and req.fb_status == "ACCEPTED" and (_can(actor, "feedback") or _can(actor, "convert")),
        "can_convert": st in (S.AWAITING_FEEDBACK.value, S.COMPLETED.value) and req.fb_status == "ACCEPTED" and _can(actor, "convert"),
        "can_cancel": st not in TERMINAL_VALUES and (own or _can(actor, "update")),
        "can_delete": (st == S.DRAFT.value and _is_creator(actor, req)) or (_can(actor, "delete") and st != S.CONVERTED.value),
        "can_new_request": req.fb_status in ("REJECTED", "ACCEPTED_WITH_CONDITIONS") and _can(actor, "create"),
        "can_attach": own or any(_can(actor, a) for a in ("update", "dispatch", "follow_up", "feedback")),
    }


TERMINAL_VALUES = tuple(s.value for s in TERMINAL)


# ── lookups ───────────────────────────────────────────────────────────
def _get_or_404(request_id: int) -> RequestSample:
    row = db.session.get(RequestSample, request_id)
    if row is None or row.deleted_at is not None:
        raise NotFoundError("Request sample was not found.")
    return row


def get_visible(actor: User, request_id: int) -> RequestSample:
    """`read` is required; somebody else's DRAFT does not exist for you."""
    _require(actor, "read")
    row = _get_or_404(request_id)
    if row.status == S.DRAFT.value and not _is_creator(actor, row):
        raise NotFoundError("Request sample was not found.")
    return row


def _event(req: RequestSample, actor: User | None, action: str, *, from_status: str | None = None,
           to_status: str | None = None, note: str | None = None, details: dict | None = None) -> None:
    db.session.add(RequestSampleEvent(
        request_id=req.id, at=_now(), user_id=actor.id if actor else None,
        user_name=actor.full_name if actor else None, action=action,
        from_status=from_status, to_status=to_status, note=note, details=details,
    ))


def _audit(actor: User, action: str, req: RequestSample, ip: str | None, **meta) -> None:
    write_audit_log(user_id=actor.id, action=action, module=MODULE, entity_type=ENTITY, entity_id=req.id,
                    metadata={"code": req.code, **meta}, ip_address=ip)


def _notify(user_id: int | None, actor: User, type_: str, title: str, message: str, req: RequestSample) -> None:
    if user_id and user_id != actor.id:
        notifications.notify(user_id, type_, title, message, link=link_for(req))


def _customer_or_error(customer_id: int) -> Customer:
    c = db.session.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise InvalidInputError("Customer was not found in the customer bank.", "customer_id")
    return c


def _rep_or_error(user_id: int) -> User:
    u = db.session.get(User, user_id)
    if u is None or not u.is_active:
        raise InvalidInputError("The sales representative is not an active user.", "sales_rep_user_id")
    return u


# ── files ─────────────────────────────────────────────────────────────
def _link_files(actor: User, req: RequestSample, ids: list[str], kind: str) -> None:
    for fid in ids:
        row = db.session.get(RequestSampleFile, fid)
        if row is None:
            raise InvalidInputError("An attached file was not found.", "file_ids")
        if row.request_id not in (None, req.id):
            raise InvalidInputError("An attached file belongs to another request.", "file_ids")
        if row.request_id is None and row.uploaded_by_user_id != actor.id:
            raise InvalidInputError("You can only attach files you uploaded.", "file_ids")
        row.request_id = req.id
        row.kind = kind


def upload_orphan(actor: User, file, kind: str) -> dict:
    """The wizard uploads before the request exists; the file is linked when the request is saved."""
    if not (_can(actor, "create") or _can(actor, "update")):
        _require(actor, "create")
    return files.file_ref(files.save_upload(file, uploaded_by_user_id=actor.id, kind=kind))


def upload_to_request(actor: User, request_id: int, file, kind: str, ip: str | None) -> dict:
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_attach"]:
        raise PermissionDeniedError("permission_denied", "You cannot attach files to this request.")
    row = files.save_upload(file, uploaded_by_user_id=actor.id, kind=kind, request_id=req.id)
    _event(req, actor, "file_added", note=row.original_name, details={"kind": row.kind})
    db.session.commit()
    return files.file_ref(row)


def download_file(actor: User, file_id: str):
    _require(actor, "read")
    row = files.get_file_or_404(file_id)
    if row.request_id is not None:
        get_visible(actor, row.request_id)
    elif row.uploaded_by_user_id != actor.id:
        raise NotFoundError("File was not found.")
    return row


def delete_file(actor: User, file_id: str, ip: str | None) -> None:
    row = files.get_file_or_404(file_id)
    req = get_visible(actor, row.request_id) if row.request_id else None
    if not (row.uploaded_by_user_id == actor.id or _can(actor, "update")):
        raise PermissionDeniedError("permission_denied", "You cannot delete this file.")
    if req is not None:
        _event(req, actor, "file_removed", note=row.original_name)
    db.session.delete(row)
    db.session.commit()


# ── validation ────────────────────────────────────────────────────────
def _validate_for_submit(req: RequestSample) -> None:
    if not req.dispatch_ref_number:
        raise InvalidInputError("The sample dispatch reference number (شماره حواله نمونه) is required.", "dispatch_ref_number")
    if not req.items:
        raise InvalidInputError("Add at least one product.", "items")
    for i, it in enumerate(req.items):
        if not it.product_name or float(it.quantity or 0) <= 0:
            raise InvalidInputError(f"Product row {i + 1}: name and quantity are required.", "items")
    for field, label in (("recipient_name", "recipient name"), ("delivery_address", "delivery address"), ("city", "city")):
        if not getattr(req, field):
            raise InvalidInputError(f"Shipping information: {label} is required.", field)


def _ensure_unique_ref(req: RequestSample | None, ref: str | None) -> None:
    """The dispatch reference is the request's identifier, so two live requests cannot share it."""
    if not ref:
        return
    q = db.session.query(RequestSample.id).filter(
        RequestSample.deleted_at.is_(None),
        db.func.lower(RequestSample.dispatch_ref_number) == ref.strip().lower(),
    )
    if req is not None and req.id is not None:
        q = q.filter(RequestSample.id != req.id)
    if q.first():
        raise ConflictError(f"A request with dispatch reference number '{ref}' already exists.")


_SCALARS = (
    "dispatch_ref_number", "required_delivery_date", "purpose", "technical_requirements", "delivery_method", "recipient_name",
    "delivery_address", "country", "city", "postal_code", "delivery_instructions", "internal_notes", "priority",
)


def _apply(req: RequestSample, payload: RequestIn) -> None:
    for f in _SCALARS:
        setattr(req, f, getattr(payload, f))
    req.items.clear()
    db.session.flush()
    for it in payload.items:
        req.items.append(RequestSampleItem(
            product_name=it.product_name, grade=it.grade, quantity=it.quantity, unit=it.unit,
            number_of_samples=it.number_of_samples, packaging=it.packaging, specifications=it.specifications,
        ))


# ── create / update / delete ──────────────────────────────────────────
def create_request(actor: User, payload: RequestIn, *, ip_address: str | None) -> RequestSample:
    _require(actor, "create")
    _customer_or_error(payload.customer_id)
    rep = _rep_or_error(payload.sales_rep_user_id) if payload.sales_rep_user_id else actor
    _ensure_unique_ref(None, payload.dispatch_ref_number)
    req = RequestSample(
        customer_id=payload.customer_id, sales_rep_user_id=rep.id, created_by_user_id=actor.id,
        status=S.DRAFT.value, requested_date=tehran_today(),
    )
    _apply(req, payload)
    db.session.add(req)
    db.session.flush()
    _link_files(actor, req, payload.file_ids, "TECHNICAL")
    _event(req, actor, "created", to_status=S.DRAFT.value)
    _audit(actor, "create", req, ip_address)
    db.session.commit()
    return req


def update_request(actor: User, request_id: int, payload: RequestIn, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    if not can_edit(actor, req):
        raise PermissionDeniedError("permission_denied", "This request cannot be edited in its current status.")
    _customer_or_error(payload.customer_id)
    _ensure_unique_ref(req, payload.dispatch_ref_number)
    req.customer_id = payload.customer_id
    if payload.sales_rep_user_id:
        req.sales_rep_user_id = _rep_or_error(payload.sales_rep_user_id).id
    _apply(req, payload)
    _link_files(actor, req, payload.file_ids, "TECHNICAL")
    _event(req, actor, "updated")
    _audit(actor, "update", req, ip_address)
    db.session.commit()
    return req


def delete_request(actor: User, request_id: int, *, ip_address: str | None) -> None:
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_delete"]:
        raise PermissionDeniedError("permission_denied", "You cannot delete this request.")
    req.deleted_at = _now()
    reminders.clear(req.id)
    _audit(actor, "delete", req, ip_address)
    db.session.commit()


def new_request_from(actor: User, request_id: int, *, ip_address: str | None) -> RequestSample:
    """A rejected / conditionally accepted sample: start a new DRAFT that stays linked to the old one."""
    src = get_visible(actor, request_id)
    if not viewer_flags(actor, src)["can_new_request"]:
        raise ConflictError("A new request can be raised only after the customer rejected the sample or accepted it with conditions.")
    req = RequestSample(
        customer_id=src.customer_id, sales_rep_user_id=src.sales_rep_user_id or actor.id, created_by_user_id=actor.id,
        status=S.DRAFT.value, requested_date=tehran_today(), parent_request_id=src.id,
    )
    for f in _SCALARS:
        if f != "dispatch_ref_number":  # a new sample needs its own dispatch reference
            setattr(req, f, getattr(src, f))
    for it in src.items:
        req.items.append(RequestSampleItem(
            product_name=it.product_name, grade=it.grade, quantity=it.quantity, unit=it.unit,
            number_of_samples=it.number_of_samples, packaging=it.packaging, specifications=it.specifications,
        ))
    db.session.add(req)
    db.session.flush()
    _event(req, actor, "created", to_status=S.DRAFT.value, note=f"Follow-up of {src.code}")
    _event(src, actor, "new_request_raised", note=req.code)
    _audit(actor, "create", req, ip_address, parent=src.code)
    db.session.commit()
    return req


# ── workflow transitions ──────────────────────────────────────────────
def transition(actor: User, request_id: int, payload: TransitionIn, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    flags = viewer_flags(actor, req)
    action, note = payload.action, payload.note
    old = req.status

    def deny(msg: str):
        raise PermissionDeniedError("permission_denied", msg)

    if action == "submit":
        if not flags["can_submit"]:
            deny("This request cannot be submitted by you in its current status.")
        _validate_for_submit(req)
        req.status, req.submitted_at = S.PENDING_APPROVAL.value, _now()
        req.reject_reason = req.hold_reason = None
        _event(req, actor, "submitted", from_status=old, to_status=req.status, note=note)
        for uid in request_ops.reviewer_ids("crm.request_sample.approve", exclude=actor.id):
            notifications.notify(uid, "SAMPLE_SUBMITTED", "درخواست نمونهٔ جدید در انتظار تأیید",
                                 f"{actor.full_name} درخواست {req.code} را ثبت کرد.", link=link_for(req))
    elif action == "approve":
        if not flags["can_approve"]:
            deny("You cannot approve this request (a request cannot be approved by the person who created it).")
        req.status, req.approved_at, req.decided_at, req.decided_by_user_id = S.APPROVED.value, _now(), _now(), actor.id
        req.hold_reason = None
        _event(req, actor, "approved", from_status=old, to_status=req.status, note=note)
        _notify(req.created_by_user_id, actor, "SAMPLE_APPROVED", "درخواست نمونه تأیید شد", f"درخواست {req.code} تأیید شد.", req)
        if req.sales_rep_user_id != req.created_by_user_id:
            _notify(req.sales_rep_user_id, actor, "SAMPLE_APPROVED", "درخواست نمونه تأیید شد", f"درخواست {req.code} تأیید شد.", req)
    elif action == "reject":
        if not flags["can_reject"]:
            deny("You cannot reject this request.")
        if not (note or "").strip():
            raise InvalidInputError("A reason is required to reject a request.", "note")
        req.status, req.reject_reason, req.decided_at, req.decided_by_user_id = S.REJECTED.value, note.strip(), _now(), actor.id
        req.closed_at = _now()
        _event(req, actor, "rejected", from_status=old, to_status=req.status, note=note)
        _notify(req.created_by_user_id, actor, "SAMPLE_REJECTED", "درخواست نمونه رد شد", f"درخواست {req.code} رد شد: {note.strip()}", req)
    elif action == "hold":
        if not flags["can_hold"]:
            deny("You cannot put this request on hold.")
        if not (note or "").strip():
            raise InvalidInputError("A reason is required to put a request on hold.", "note")
        req.status, req.hold_reason = S.ON_HOLD.value, note.strip()
        _event(req, actor, "on_hold", from_status=old, to_status=req.status, note=note)
        _notify(req.created_by_user_id, actor, "SAMPLE_ON_HOLD", "درخواست نمونه متوقف شد", f"درخواست {req.code}: {note.strip()}", req)
    elif action == "resume":
        if not flags["can_resume"]:
            deny("You cannot resume this request.")
        req.status, req.hold_reason = S.PENDING_APPROVAL.value, None
        _event(req, actor, "resumed", from_status=old, to_status=req.status, note=note)
    elif action == "complete":
        if not flags["can_complete"]:
            deny("A request can be completed only after the customer ACCEPTED the sample.")
        req.status, req.closed_at = S.COMPLETED.value, _now()
        _event(req, actor, "completed", from_status=old, to_status=req.status, note=note)
    elif action == "cancel":
        if not flags["can_cancel"]:
            deny("You cannot cancel this request.")
        if not (note or "").strip():
            raise InvalidInputError("A reason is required to cancel a request.", "note")
        req.status, req.cancel_reason, req.closed_at = S.CANCELLED.value, note.strip(), _now()
        _event(req, actor, "cancelled", from_status=old, to_status=req.status, note=note)
    if req.status != old:
        reminders.clear(req.id)  # the request left its stage: its unread reminders no longer apply
    _audit(actor, action, req, ip_address, from_status=old, to_status=req.status)
    db.session.commit()
    return req


# ── dispatch (shipments) ──────────────────────────────────────────────
def add_dispatch(actor: User, request_id: int, payload: DispatchIn, *, ip_address: str | None) -> RequestSample:
    """Step «ثبت اطلاعات ارسال»: the sample was handed to the dispatch unit / carrier. Recording the
    shipment (with `all_shipped`) declares the request «ارسال‌شده» (DISPATCHED). A partial shipment
    (`all_shipped` false) keeps it APPROVED, i.e. still waiting to be sent."""
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_dispatch"]:
        raise PermissionDeniedError("permission_denied", "Shipments can be recorded only for an approved request, with the dispatch permission.")
    row = RequestSampleDispatch(
        request_id=req.id, dispatch_date=payload.dispatch_date, reference_number=payload.reference_number,
        delivery_method=payload.delivery_method, tracking_number=payload.tracking_number, carrier=payload.carrier,
        shipped_quantity=payload.shipped_quantity, unit=payload.unit, recipient_name=payload.recipient_name,
        notes=payload.notes, created_by_user_id=actor.id,
    )
    req.dispatches.append(row)
    db.session.flush()
    _link_files(actor, req, payload.file_ids, "DISPATCH")
    old = req.status
    _event(req, actor, "dispatch_added", note=payload.reference_number,
           details={"tracking": payload.tracking_number, "qty": float(payload.shipped_quantity) if payload.shipped_quantity else None})
    if req.first_dispatched_at is None:
        req.first_dispatched_at = _now()
    if old == S.APPROVED.value and payload.all_shipped:
        req.status = S.DISPATCHED.value
        _event(req, actor, "dispatched", from_status=old, to_status=req.status)
        _notify(req.sales_rep_user_id, actor, "SAMPLE_DISPATCHED", "نمونه ارسال شد",
                f"نمونهٔ درخواست {req.code} ارسال شد؛ پس از دریافت توسط مشتری، تحویل را تأیید کنید.", req)
        reminders.clear(req.id, ("ship",))
    _audit(actor, "dispatch", req, ip_address, reference=payload.reference_number)
    db.session.commit()
    return req


def confirm_delivery(actor: User, request_id: int, payload: DeliveryIn, *, ip_address: str | None) -> RequestSample:
    """The customer received the sample: DISPATCHED -> AWAITING_FEEDBACK (follow-up phase)."""
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_confirm_delivery"]:
        raise PermissionDeniedError("permission_denied", "Receipt can be confirmed only for a dispatched request, by its owner or a user with dispatch / follow-up permission.")
    first = req.first_dispatched_at
    if first and payload.delivered_date < to_tehran(first).date():
        raise InvalidInputError("The delivery date cannot be before the dispatch date.", "delivered_date")
    if payload.delivered_date > tehran_today():
        raise InvalidInputError("The delivery date cannot be in the future.", "delivered_date")
    old = req.status
    req.status = S.AWAITING_FEEDBACK.value
    req.delivered_at, req.delivery_received_by, req.delivery_note = payload.delivered_date, payload.received_by, payload.note
    _event(req, actor, "delivered", from_status=old, to_status=req.status, note=payload.note,
           details={"date": payload.delivered_date.isoformat(), "received_by": payload.received_by})
    _notify(req.sales_rep_user_id, actor, "SAMPLE_DELIVERED", "نمونه تحویل مشتری شد",
            f"دریافت نمونهٔ درخواست {req.code} توسط مشتری ثبت شد؛ پیگیری را ثبت کنید.", req)
    reminders.clear(req.id, ("ship", "deliver"))
    _audit(actor, "confirm_delivery", req, ip_address, date=payload.delivered_date.isoformat())
    db.session.commit()
    return req


def delete_dispatch(actor: User, request_id: int, dispatch_id: int, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    if not _can(actor, "dispatch") or req.status in TERMINAL_VALUES:
        raise PermissionDeniedError("permission_denied", "You cannot remove this shipment.")
    row = next((d for d in req.dispatches if d.id == dispatch_id), None)
    if row is None:
        raise NotFoundError("Shipment was not found.")
    req.dispatches.remove(row)
    _event(req, actor, "dispatch_removed", note=row.reference_number)
    db.session.commit()
    return req


# ── follow-ups ────────────────────────────────────────────────────────
def _followup_or_404(req: RequestSample, followup_id: int) -> RequestSampleFollowUp:
    row = next((f for f in req.followups if f.id == followup_id), None)
    if row is None:
        raise NotFoundError("Follow-up was not found.")
    return row


def _check_followup_user(payload: FollowUpIn) -> None:
    if payload.responsible_user_id:
        _rep_or_error(payload.responsible_user_id)
    if payload.next_followup_date and payload.next_followup_date < payload.followup_date:
        raise InvalidInputError("The next follow-up date cannot be before this follow-up.", "next_followup_date")


def add_followup(actor: User, request_id: int, payload: FollowUpIn, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_follow_up"]:
        raise PermissionDeniedError("permission_denied", "Follow-ups can be recorded after the sample is dispatched, with the follow-up permission.")
    _check_followup_user(payload)
    row = RequestSampleFollowUp(
        request_id=req.id, followup_date=payload.followup_date, method=payload.method,
        contact_person=payload.contact_person, result=payload.result, customer_response=payload.customer_response,
        next_followup_date=payload.next_followup_date, responsible_user_id=payload.responsible_user_id or actor.id,
        internal_notes=payload.internal_notes, created_by_user_id=actor.id,
    )
    req.followups.append(row)
    db.session.flush()
    _link_files(actor, req, payload.file_ids, "FOLLOWUP")
    reminders.clear(req.id, ("followup", "due"))
    _event(req, actor, "followup_added", note=payload.result, details={"method": payload.method})
    _audit(actor, "follow_up", req, ip_address, method=payload.method)
    db.session.commit()
    return req


def update_followup(actor: User, request_id: int, followup_id: int, payload: FollowUpIn, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    row = _followup_or_404(req, followup_id)
    if not _can(actor, "follow_up") or not (row.created_by_user_id == actor.id or _can(actor, "update")) or req.status in TERMINAL_VALUES:
        raise PermissionDeniedError("permission_denied", "You cannot edit this follow-up.")
    _check_followup_user(payload)
    for f in ("followup_date", "method", "contact_person", "result", "customer_response", "next_followup_date", "internal_notes"):
        setattr(row, f, getattr(payload, f))
    if payload.responsible_user_id:
        row.responsible_user_id = payload.responsible_user_id
    _link_files(actor, req, payload.file_ids, "FOLLOWUP")
    reminders.clear(req.id, ("followup", "due"))
    _event(req, actor, "followup_updated", note=payload.result)
    db.session.commit()
    return req


def delete_followup(actor: User, request_id: int, followup_id: int, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    row = _followup_or_404(req, followup_id)
    if not _can(actor, "follow_up") or not (row.created_by_user_id == actor.id or _can(actor, "update")) or req.status in TERMINAL_VALUES:
        raise PermissionDeniedError("permission_denied", "You cannot delete this follow-up.")
    req.followups.remove(row)
    _event(req, actor, "followup_removed")
    db.session.commit()
    return req


# ── final customer feedback ───────────────────────────────────────────
def set_feedback(actor: User, request_id: int, payload: FeedbackIn, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_feedback"]:
        raise PermissionDeniedError("permission_denied", "Final feedback can be recorded after the sample is dispatched, with the feedback permission.")
    st = payload.feedback_status
    if st == "REJECTED" and not payload.rejection_reason:
        raise InvalidInputError("The reason the sample was not accepted is required.", "rejection_reason")
    if st == "ACCEPTED_WITH_CONDITIONS" and not payload.customer_comments:
        raise InvalidInputError("Write the customer's conditions in the comments.", "customer_comments")
    if payload.feedback_date > tehran_today():
        raise InvalidInputError("The feedback date cannot be in the future.", "feedback_date")
    old = req.status
    req.fb_status, req.fb_date = st, payload.feedback_date
    req.fb_product_evaluation, req.fb_technical_acceptance = payload.product_evaluation, payload.technical_acceptance
    req.fb_comments, req.fb_rejection_reason = payload.customer_comments, payload.rejection_reason
    req.fb_suggestions, req.fb_evaluated_by = payload.improvement_suggestions, payload.evaluated_by
    req.fb_recorded_by_user_id, req.fb_recorded_at = actor.id, _now()
    _link_files(actor, req, payload.file_ids, "FEEDBACK")
    if st == "REJECTED":  # closed with a clear outcome; a corrected / new sample is a NEW linked request
        req.status, req.closed_at = S.COMPLETED.value, _now()
    elif old == S.COMPLETED.value and st != "REJECTED":
        req.status, req.closed_at = S.AWAITING_FEEDBACK.value, None  # the outcome changed: back to follow-up
    if st in ("ACCEPTED", "REJECTED", "ACCEPTED_WITH_CONDITIONS"):
        reminders.clear(req.id)  # the customer decided: no more follow-up reminders
    _event(req, actor, "feedback_recorded", from_status=old, to_status=req.status, note=payload.customer_comments,
           details={"feedback_status": st})
    _notify(req.sales_rep_user_id, actor, "SAMPLE_FEEDBACK", "بازخورد نهایی مشتری ثبت شد", f"درخواست {req.code}: {st}", req)
    _audit(actor, "feedback", req, ip_address, feedback_status=st)
    db.session.commit()
    return req


def convert_to_sales(actor: User, request_id: int, sale_id: int | None, note: str | None, *, ip_address: str | None) -> RequestSample:
    req = get_visible(actor, request_id)
    if not viewer_flags(actor, req)["can_convert"]:
        raise PermissionDeniedError("permission_denied", "Only a sample the customer ACCEPTED can be converted, with the convert permission.")
    if sale_id is not None:
        sale = db.session.get(CrmSale, sale_id)
        if sale is None or sale.deleted_at is not None:
            raise InvalidInputError("The selected sale was not found.", "sale_id")
        if sale.customer_id != req.customer_id:
            raise InvalidInputError("That sale belongs to another customer.", "sale_id")
        req.converted_sale_id = sale.id
    old = req.status
    req.status, req.conversion_note, req.converted_at = S.CONVERTED.value, (note or None), _now()
    req.closed_at = req.closed_at or _now()
    _event(req, actor, "converted", from_status=old, to_status=req.status, note=note, details={"sale_id": sale_id})
    _audit(actor, "convert", req, ip_address, sale_id=sale_id)
    db.session.commit()
    return req


# ── list / filters / dump ─────────────────────────────────────────────
def parse_filters(args) -> dict:
    def many(name):
        return [s.strip() for raw in args.getlist(name) for s in raw.split(",") if s.strip()]

    def d(name):
        raw = (args.get(name) or "").strip()
        try:
            return date.fromisoformat(raw) if raw else None
        except ValueError:
            raise InvalidInputError(f"{name} must be YYYY-MM-DD.", name)

    f = {
        "search": (args.get("search") or "").strip(), "statuses": many("status"), "priorities": many("priority"),
        "customer_id": args.get("customer_id", type=int), "product": (args.get("product") or "").strip(),
        "grade": (args.get("grade") or "").strip(), "rep_id": args.get("rep_id", type=int),
        "feedback": (args.get("feedback") or "").strip(), "date_from": d("date_from"), "date_to": d("date_to"),
        "followup_overdue": (args.get("followup_overdue") or "").lower() in ("1", "true"),
        "mine": (args.get("mine") or "").lower() in ("1", "true"),
    }
    if f["date_from"] and f["date_to"] and f["date_from"] > f["date_to"]:
        raise InvalidInputError("date_from is after date_to.", "date_from")
    return f


def _query(actor: User, f: dict):
    q = db.session.query(RequestSample).join(Customer, Customer.id == RequestSample.customer_id).filter(
        RequestSample.deleted_at.is_(None),
        or_(RequestSample.status != S.DRAFT.value, RequestSample.created_by_user_id == actor.id),
    )
    if f["search"]:
        term = f["search"]
        conds = []
        upper = term.upper().replace(" ", "")
        if upper.startswith("RS-") and upper[3:].isdigit():
            conds.append(RequestSample.id == int(upper[3:]))
        match = _customer_text_match(term)
        if match is not None:
            conds.append(match)
        like = f"%{term.lower().replace('%', '').replace('_', '')}%"
        conds.append(db.func.lower(db.func.coalesce(RequestSample.dispatch_ref_number, "")).like(like))
        conds.append(exists().where(and_(
            RequestSampleItem.request_id == RequestSample.id,
            or_(db.func.lower(RequestSampleItem.product_name).like(like), db.func.lower(db.func.coalesce(RequestSampleItem.grade, "")).like(like)),
        )))
        q = q.filter(or_(*conds))
    if f["statuses"]:
        q = q.filter(RequestSample.status.in_(f["statuses"]))
    if f["priorities"]:
        q = q.filter(RequestSample.priority.in_(f["priorities"]))
    if f["customer_id"]:
        q = q.filter(RequestSample.customer_id == f["customer_id"])
    if f["rep_id"]:
        q = q.filter(RequestSample.sales_rep_user_id == f["rep_id"])
    if f["mine"]:
        q = q.filter(or_(RequestSample.sales_rep_user_id == actor.id, RequestSample.created_by_user_id == actor.id))
    if f["feedback"]:
        q = q.filter(RequestSample.fb_status == f["feedback"]) if f["feedback"] != "NONE" else q.filter(RequestSample.fb_status.is_(None))
    if f["date_from"]:
        q = q.filter(RequestSample.requested_date >= f["date_from"])
    if f["date_to"]:
        q = q.filter(RequestSample.requested_date <= f["date_to"])
    for field, col in (("product", RequestSampleItem.product_name), ("grade", RequestSampleItem.grade)):
        if f[field]:
            q = q.filter(exists().where(and_(RequestSampleItem.request_id == RequestSample.id, col == f[field])))
    if f["followup_overdue"]:
        today = tehran_today()
        q = q.filter(
            RequestSample.status.in_(FOLLOWUP_OPEN),
            exists().where(and_(
                RequestSampleFollowUp.request_id == RequestSample.id,
                RequestSampleFollowUp.next_followup_date.isnot(None),
                RequestSampleFollowUp.next_followup_date < today,
            )),
        )
    return q


_SORTS = {
    "id": RequestSample.id, "requested_date": RequestSample.requested_date, "status": RequestSample.status,
    "priority": RequestSample.priority, "customer": Customer.company_name, "feedback": RequestSample.fb_status,
}


def list_requests(actor: User, f: dict, *, page: int, per_page: int, sort: str = "-id"):
    _require(actor, "read")
    q = _query(actor, f)
    total = q.order_by(None).count()
    key = sort.lstrip("-")
    col = _SORTS.get(key, RequestSample.id)
    q = q.order_by(col.desc() if sort.startswith("-") else col.asc(), RequestSample.id.desc())
    return q.offset((page - 1) * per_page).limit(per_page).all(), total


def all_requests(actor: User, f: dict) -> list[RequestSample]:
    _require(actor, "read")
    return _query(actor, f).order_by(RequestSample.id.desc()).limit(10000).all()


def options(actor: User) -> dict:
    """Pickers for filters: reps, product / grade names used, statuses are static on the client."""
    _require(actor, "read")
    reps = (
        db.session.query(User.id, User.full_name).join(RequestSample, RequestSample.sales_rep_user_id == User.id)
        .filter(RequestSample.deleted_at.is_(None)).distinct().order_by(User.full_name).all()
    )
    products = [r[0] for r in db.session.query(RequestSampleItem.product_name).distinct().order_by(RequestSampleItem.product_name).all()]
    grades = [r[0] for r in db.session.query(RequestSampleItem.grade).filter(RequestSampleItem.grade.isnot(None)).distinct().order_by(RequestSampleItem.grade).all()]
    return {"reps": [{"id": i, "name": n} for i, n in reps], "products": products, "grades": grades}


def product_options(actor: User) -> list[dict]:
    """Customer-bank pick-lists the request form needs (consumed products + grades), served under the
    request-sample permission so a rep without `crm.customer.read` still sees the lists."""
    _require(actor, "read")
    rows = (
        db.session.query(CustomerOptionItem)
        .filter(CustomerOptionItem.kind.in_([OptionKind.CONSUMED, OptionKind.GRADE]))
        .order_by(CustomerOptionItem.kind, CustomerOptionItem.sort_order, CustomerOptionItem.name).all()
    )
    return [_option_dict(o) for o in rows]


def rep_candidates(actor: User) -> list[dict]:
    """Active users who can own a request (anyone who may create one)."""
    _require(actor, "read")
    users = db.session.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).limit(500).all()
    return [{"id": u.id, "name": u.full_name} for u in users]


def _iso(dt: datetime | None) -> str | None:
    return None if dt is None else (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def _stamp(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    local = to_tehran(dt)
    return f"{format_jalali(local.date())} {local:%H:%M}"


def _num(x):
    return None if x is None else float(x)


def _customer_ref(c: Customer, detail: bool) -> dict:
    ref = {"id": c.id, "name": c.display_name, "brand": c.brand_name, "province": c.factory_province, "city": c.factory_city}
    if detail:
        ref.update({
            "company_name": c.company_name, "customer_type": getattr(c.customer_type, "value", c.customer_type),
            "company_phone": c.company_phone, "category": c.category,
            "contacts": [
                {"name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(), "position": p.get("position"),
                 "mobile": p.get("mobile"), "landline": p.get("landline")}
                for p in (c.contacts or []) if isinstance(p, dict)
            ],
        })
    return ref


def _qty_label(items) -> str:
    if not items:
        return ""
    first = items[0]
    q = float(first.quantity)
    text = f"{q:g} {first.unit}"
    return text if len(items) == 1 else f"{text} (+{len(items) - 1})"


def dump(req: RequestSample, actor: User, *, detail: bool = False) -> dict:
    items = list(req.items)
    data = {
        "id": req.id, "code": req.code, "status": req.status, "priority": req.priority,
        "customer": _customer_ref(req.customer, detail),
        "sales_rep": {"id": req.sales_rep_user_id, "name": req.sales_rep.full_name if req.sales_rep else None},
        "requested_date": req.requested_date.isoformat(), "required_delivery_date": req.required_delivery_date.isoformat() if req.required_delivery_date else None,
        "dispatch_ref_number": req.dispatch_ref_number,
        "product": items[0].product_name if items else None, "grade": items[0].grade if items else None,
        "items_count": len(items), "quantity_label": _qty_label(items),
        "feedback_status": req.fb_status, "parent_request_id": req.parent_request_id,
        "created_by_name": req.created_by_name, "created_at": _iso(req.created_at),
        "next_followup_date": next((f.next_followup_date.isoformat() for f in sorted(req.followups, key=lambda x: x.next_followup_date or date.max) if f.next_followup_date and f.next_followup_date >= tehran_today()), None),
        "followup_overdue": req.status in FOLLOWUP_OPEN and any(f.next_followup_date and f.next_followup_date < tehran_today() for f in req.followups[-1:]),
        "my_actions": viewer_flags(actor, req),
    }
    if not detail:
        return data
    data.update({
        "purpose": req.purpose, "technical_requirements": req.technical_requirements,
        "delivery_method": req.delivery_method, "recipient_name": req.recipient_name, "delivery_address": req.delivery_address,
        "country": req.country, "city": req.city, "postal_code": req.postal_code, "delivery_instructions": req.delivery_instructions,
        "internal_notes": req.internal_notes if (_is_own(actor, req) or _can(actor, "update") or _can(actor, "approve")) else None,
        "reject_reason": req.reject_reason, "hold_reason": req.hold_reason, "cancel_reason": req.cancel_reason,
        "submitted_at": _iso(req.submitted_at), "approved_at": _iso(req.approved_at), "decided_at": _iso(req.decided_at),
        "first_dispatched_at": _iso(req.first_dispatched_at), "closed_at": _iso(req.closed_at),
        "delivered_at": req.delivered_at.isoformat() if req.delivered_at else None,
        "delivery_received_by": req.delivery_received_by, "delivery_note": req.delivery_note,
        "items": [{
            "id": i.id, "product_name": i.product_name, "grade": i.grade,
            "quantity": _num(i.quantity), "unit": i.unit,
            "number_of_samples": i.number_of_samples, "packaging": i.packaging, "specifications": i.specifications,
        } for i in items],
        "dispatches": [{
            "id": d.id, "dispatch_date": d.dispatch_date.isoformat(), "reference_number": d.reference_number,
            "delivery_method": d.delivery_method, "tracking_number": d.tracking_number, "carrier": d.carrier,
            "shipped_quantity": _num(d.shipped_quantity), "unit": d.unit, "recipient_name": d.recipient_name,
            "notes": d.notes, "created_by_name": d.creator_name, "created_at": _iso(d.created_at),
        } for d in req.dispatches],
        "followups": [{
            "id": f.id, "followup_date": f.followup_date.isoformat(), "method": f.method, "contact_person": f.contact_person,
            "result": f.result, "customer_response": f.customer_response,
            "next_followup_date": f.next_followup_date.isoformat() if f.next_followup_date else None,
            "responsible": {"id": f.responsible_user_id, "name": f.responsible.full_name if f.responsible else None},
            "internal_notes": f.internal_notes, "created_by_name": f.creator_name, "created_by_user_id": f.created_by_user_id,
            "created_at": _iso(f.created_at),
            "overdue": bool(f.next_followup_date and f.next_followup_date < tehran_today() and req.status in FOLLOWUP_OPEN and f is req.followups[-1]),
            "can_edit": _can(actor, "follow_up") and (f.created_by_user_id == actor.id or _can(actor, "update")) and req.status not in TERMINAL_VALUES,
        } for f in req.followups],
        "feedback": None if not req.fb_status else {
            "status": req.fb_status, "date": req.fb_date.isoformat() if req.fb_date else None,
            "product_evaluation": req.fb_product_evaluation, "technical_acceptance": req.fb_technical_acceptance,
            "customer_comments": req.fb_comments, "rejection_reason": req.fb_rejection_reason,
            "improvement_suggestions": req.fb_suggestions, "evaluated_by": req.fb_evaluated_by,
            "recorded_at": _iso(req.fb_recorded_at),
        },
        "conversion": None if req.converted_at is None else {
            "sale_id": req.converted_sale_id, "note": req.conversion_note, "converted_at": _iso(req.converted_at),
        },
        "files": [files.file_ref(f) for f in db.session.query(RequestSampleFile).filter(RequestSampleFile.request_id == req.id).order_by(RequestSampleFile.created_at)],
        "events": [{
            "id": e.id, "at": _iso(e.at), "at_display": _stamp(e.at), "user_name": e.user_name, "action": e.action,
            "from_status": e.from_status, "to_status": e.to_status, "note": e.note, "details": e.details,
        } for e in db.session.query(RequestSampleEvent).filter(RequestSampleEvent.request_id == req.id).order_by(RequestSampleEvent.id)],
    })
    if req.parent_request_id:
        parent = db.session.get(RequestSample, req.parent_request_id)
        data["parent"] = {"id": parent.id, "code": parent.code} if parent else None
    data["children"] = [
        {"id": c.id, "code": c.code, "status": c.status}
        for c in db.session.query(RequestSample).filter(RequestSample.parent_request_id == req.id, RequestSample.deleted_at.is_(None))
    ]
    return data


# ── analytics ─────────────────────────────────────────────────────────
def _bucket(d: date, gran: str):
    if gran == "day":
        return d.isoformat(), format_jalali(d)
    if gran == "week":
        start = d - timedelta(days=(d.weekday() + 2) % 7)  # weeks start on Saturday
        return start.isoformat(), f"هفتهٔ {format_jalali(start)}"
    j = to_jalali(d)
    return f"{j[0]}-{j[1]:02d}", f"{JALALI_MONTH_NAMES[j[1] - 1]} {j[0]}"


def analytics(actor: User, f: dict, *, granularity: str = "month", top: int = 8) -> dict:
    rows = all_requests(actor, f)
    rows = [r for r in rows if r.status != S.DRAFT.value]  # drafts are not requests yet
    gran = granularity if granularity in ("day", "week", "month") else "month"
    by_status = Counter(r.status for r in rows)
    dispatched = [r for r in rows if r.first_dispatched_at is not None]
    converted = [r for r in rows if r.status == S.CONVERTED.value]
    kpis = {
        "total": len(rows),
        "pending": by_status[S.PENDING_APPROVAL.value] + by_status[S.NEW_REQUEST.value],
        "approved": sum(1 for r in rows if r.approved_at is not None),
        "dispatched": len(dispatched),
        "rejected": by_status[S.REJECTED.value],
        "awaiting_feedback": by_status[S.AWAITING_FEEDBACK.value],
        "converted": len(converted),
        "on_hold": by_status[S.ON_HOLD.value],
    }
    # trend
    buckets: dict[str, dict] = {}
    for r in rows:
        key, label = _bucket(r.requested_date, gran)
        b = buckets.setdefault(key, {"key": key, "label": label, "count": 0})
        b["count"] += 1
    trend = [buckets[k] for k in sorted(buckets)]
    # top products
    prod: dict[tuple, dict] = {}
    for r in rows:
        seen = set()
        for it in r.items:
            k = (it.product_name, it.grade or "")
            p = prod.setdefault(k, {"product": it.product_name, "grade": it.grade, "requests": 0, "quantity_kg": 0.0})
            if k not in seen:
                p["requests"] += 1
                seen.add(k)
            p["quantity_kg"] += float(it.quantity) * KG_PER.get(it.unit, 0.0)
    top_products = sorted(prod.values(), key=lambda p: (-p["requests"], -p["quantity_kg"]))[: max(3, min(top, 20))]
    # per sales rep
    reps: dict[int | None, dict] = defaultdict(lambda: {"requests": 0, "approved": 0, "rejected": 0, "dispatched": 0, "accepted": 0, "converted": 0})
    names: dict[int | None, str] = {}
    for r in rows:
        rid = r.sales_rep_user_id
        names[rid] = r.sales_rep.full_name if r.sales_rep else "—"
        d = reps[rid]
        d["requests"] += 1
        d["approved"] += r.approved_at is not None
        d["rejected"] += r.status == S.REJECTED.value
        d["dispatched"] += r.first_dispatched_at is not None
        d["accepted"] += r.fb_status == "ACCEPTED"
        d["converted"] += r.status == S.CONVERTED.value
    sales_performance = []
    for rid, d in reps.items():
        decided = d["approved"] + d["rejected"]
        sales_performance.append({
            "rep_id": rid, "name": names[rid], **d,
            "approval_rate": round(100 * d["approved"] / decided) if decided else None,
            "conversion_rate": round(100 * d["converted"] / d["dispatched"]) if d["dispatched"] else None,
        })
    sales_performance.sort(key=lambda x: -x["requests"])
    # feedback analysis (final feedback only)
    fb = Counter(r.fb_status for r in rows if r.fb_status)
    decided_fb = fb["ACCEPTED"] + fb["REJECTED"] + fb["ACCEPTED_WITH_CONDITIONS"]
    feedback = {
        "counts": dict(fb), "total": sum(fb.values()),
        "accepted_pct": round(100 * fb["ACCEPTED"] / decided_fb) if decided_fb else None,
        "rejected_pct": round(100 * fb["REJECTED"] / decided_fb) if decided_fb else None,
        "conditional_pct": round(100 * fb["ACCEPTED_WITH_CONDITIONS"] / decided_fb) if decided_fb else None,
    }
    return {
        "kpis": kpis, "trend": trend, "granularity": gran,
        "status_distribution": [{"status": k, "count": v} for k, v in by_status.most_common()],
        "top_products": top_products, "sales_performance": sales_performance, "feedback": feedback,
        "conversion": {
            "dispatched": len(dispatched), "converted": len(converted),
            "rate": round(100 * len(converted) / len(dispatched)) if dispatched else None,
        },
    }
