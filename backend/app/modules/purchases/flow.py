"""
Item-based purchase flow (flow_version = 2) -- warehouse -> procurement -> manager -> finance -> delivery.

Every goods line (`purchase_items`) carries its OWN status, supply place, quotations, manager decision, payment
and warehouse receipt; the request only groups them under one typed number and its status is DERIVED from them.

Who may do what (each check is `procurement.purchase.<action>`, GLOBAL, enforced here -- never only in the UI):
    warehouse  register a request, edit it after «استرداد جهت اصلاح», see every status, mark an item delivered,
               upload its receipt (no prices are shown to a user who only has this permission)
    procure    procurement cartable: request status, local / non-local, quotations, shipping, delivery, cancel an item
    manager    approve (choosing one quotation) or return each item
    finance    record the cash / cheque payment of each approved item, then hand the request back to procurement
    settings   requesting-unit / request-type lists and the allowed delivery time per priority
    read       view everything, KPIs, exports (no changes)

Item status:   PENDING -> INQUIRY -> AWAITING_APPROVAL -> IN_FINANCE -> PAID -> SHIPPING -> DELIVERED   (CANCELLED)
               a manager «return» sends an item AWAITING_APPROVAL -> INQUIRY
Request status (stored in purchase_requests.status):
    UNDER_REVIEW (set when registered) ⇄ SOURCING, RETURNED, VOID                          -- set by procurement
    REFERRED_FINANCE / FOLLOW_UP / PARTIAL_DELIVERY / COMPLETED                              -- computed from the items
Nothing recorded in an earlier stage is overwritten or deleted without the permission of that stage; every change
is written to `purchase_events` (user + time + item) and the important ones to the shared audit log.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.orm import selectinload

from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.purchases import labels as L
from app.modules.purchases import notifications as purchase_notifications
from app.modules.purchases import services as S
from app.modules.purchases.flow_schemas import (
    FinanceReturnIn, FlowItemIn, FlowRequestIn, ItemStatusIn, ManagerDecisionIn, OptionIn, PaymentIn, QuoteIn, SlaIn,
)
from app.modules.purchases.models import (
    ItemStatus, PayMethod, PurchaseEvent, PurchaseFile, PurchaseItem, PurchaseItemPayment, PurchaseItemQuote,
    PurchaseOption, PurchasePriority, PurchaseProduct, PurchaseRequest, PurchaseSla, PurchaseStatus, PurchaseSubject,
    ReviewStatus, SupplyPlace,
)
from app.modules.suppliers.models import Supplier
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.utils.jalali import format_jalali, tehran_today, to_tehran

IS = ItemStatus
PS = PurchaseStatus
MANUAL_STATUSES = (PS.UNDER_REVIEW, PS.SOURCING, PS.RETURNED, PS.VOID)
CLOSED_FLOW = (PS.COMPLETED, PS.VOID)
PROGRESSED = (IS.IN_FINANCE, IS.PAID, IS.SHIPPING, IS.DELIVERED)      # past the manager: procurement alone can no longer undo
QUOTE_EDITABLE = (IS.INQUIRY,)
DEFAULT_SLA = {"NORMAL": (14, "DAYS"), "URGENT": (7, "DAYS"), "EMERGENCY": (2, "DAYS")}
KINDS = {"UNIT": "واحد متقاضی", "REQUEST_TYPE": "نوع درخواست"}


# ── permissions / small helpers ──────────────────────────────────────
def _mine(actor: User) -> dict:
    return {a: S.can(actor, a) for a in ("read", "warehouse", "procure", "manager", "finance", "settings")}


def _money_visible(actor: User, item: PurchaseItem) -> bool:
    """Warehouse-only users never see prices; finance sees them for items that reached it."""
    m = _mine(actor)
    if m["read"] or m["procure"] or m["manager"]:
        return True
    return m["finance"] and item.item_status in PROGRESSED


def _now() -> datetime:
    return S._now()


def _hours(delta: timedelta) -> float:
    return round(delta.total_seconds() / 3600, 1)


def _stamp(dt):
    if dt is None:
        return None
    local = to_tehran(dt)
    return f"{format_jalali(local.date())} {local:%H:%M}"


def _d(value):
    return value.isoformat() if value else None


def _j(value):
    return format_jalali(value) if value else None


def _ev(req: PurchaseRequest, actor: User, *, item: PurchaseItem | None = None, kind: str = "STATUS",
        from_status=None, to_status=None, note: str | None = None) -> None:
    db.session.add(PurchaseEvent(
        request_id=req.id, kind=kind, item_id=item.id if item is not None else None,
        from_status=getattr(from_status, "value", from_status), to_status=getattr(to_status, "value", to_status),
        note=note, user_id=actor.id, user_name=(actor.full_name or "")[:200] or None, created_at=_now()))
    # who needs to hear about this step (bell + push); see purchases/notifications.py
    purchase_notifications.on_event(req, actor, item=item, kind=kind, from_status=from_status, to_status=to_status, note=note)


def _audit(actor: User, req: PurchaseRequest, action: str, meta: dict | None, ip: str | None) -> None:
    S._audit(actor, req, action, meta, ip)


def _claim_file(actor: User, req: PurchaseRequest, file_id: str | None, field: str, label: str) -> PurchaseFile | None:
    """An uploaded file may be attached once, by the person who uploaded it (or to the same request)."""
    if not file_id:
        return None
    row = db.session.get(PurchaseFile, file_id)
    ok = row is not None and (row.request_id == req.id or (row.request_id is None and row.uploaded_by_user_id == actor.id))
    S._need(ok, f"فایل «{label}» معتبر نیست؛ آن را دوباره بارگذاری کنید.", field)
    row.request_id = req.id
    return row


# ── allowed delivery time (SLA) ──────────────────────────────────────
def sla_map() -> dict[str, tuple[int, str]]:
    out = dict(DEFAULT_SLA)
    for r in db.session.scalars(select(PurchaseSla)):
        out[r.priority] = (r.amount, r.unit)
    return out


def _delta(amount: int, unit: str) -> timedelta:
    return timedelta(hours=amount) if unit == "HOURS" else timedelta(days=amount)


def timing(req: PurchaseRequest, item: PurchaseItem, sla: dict, now: datetime) -> dict | None:
    """Base = the registration moment of the request, allowed time = the one of the ITEM's priority."""
    if item.item_status == IS.CANCELLED:
        return None
    base = req.submitted_at or req.created_at
    pr = (item.priority or PurchasePriority.NORMAL).value
    amount, unit = sla.get(pr, DEFAULT_SLA[pr])
    deadline = base + _delta(amount, unit)
    done = item.delivered_at
    end = done or now
    out = {"deadline": _stamp(deadline), "deadline_iso": deadline.isoformat(), "allowed": amount, "allowed_unit": unit,
           "elapsed_hours": _hours(end - base), "delivered": done is not None,
           "remaining_hours": None, "delay_hours": 0.0, "on_time": None, "overdue": False}
    if done is not None:
        out["on_time"] = done <= deadline
        out["delay_hours"] = _hours(max(done - deadline, timedelta(0)))
    else:
        out["remaining_hours"] = _hours(deadline - now)
        out["overdue"] = deadline < now
        out["delay_hours"] = _hours(max(now - deadline, timedelta(0)))
    return out


# ── loading ──────────────────────────────────────────────────────────
def _stmt():
    return select(PurchaseRequest).where(PurchaseRequest.deleted_at.is_(None), PurchaseRequest.flow_version == 2)


def _load(request_id: int) -> PurchaseRequest:
    req = db.session.scalars(
        _stmt().where(PurchaseRequest.id == request_id).options(
            selectinload(PurchaseRequest.items).selectinload(PurchaseItem.quotes).selectinload(PurchaseItemQuote.file),
            selectinload(PurchaseRequest.items).selectinload(PurchaseItem.payment),
            selectinload(PurchaseRequest.items).selectinload(PurchaseItem.receipt_file),
        )).first()
    if req is None:
        raise NotFoundError("درخواست خرید پیدا نشد.")
    return req


def _item(req: PurchaseRequest, item_id: int) -> PurchaseItem:
    for it in req.items:
        if it.id == item_id:
            return it
    raise NotFoundError("کالا در این درخواست پیدا نشد.")


def get_request(actor: User, request_id: int) -> PurchaseRequest:
    S.require_any(actor, S.READERS)
    req = _load(request_id)
    m = _mine(actor)
    if m["finance"] and not (m["read"] or m["warehouse"] or m["procure"] or m["manager"]):
        # finance only works on requests that reached it
        if not any(i.item_status in PROGRESSED for i in req.items):
            raise NotFoundError("درخواست خرید پیدا نشد.")
    return req


# ── status derivation ────────────────────────────────────────────────
def derive_status(req: PurchaseRequest) -> PurchaseStatus:
    """The request status as computed from its items (only applied once a request left the manual stages)."""
    active = [i for i in req.items if i.item_status != IS.CANCELLED]
    if not active:
        return PS.VOID
    st = [i.item_status for i in active]
    if all(s == IS.DELIVERED for s in st):
        return PS.COMPLETED
    if any(s == IS.IN_FINANCE for s in st):
        return PS.REFERRED_FINANCE
    if any(s == IS.DELIVERED for s in st):
        return PS.PARTIAL_DELIVERY
    if any(s in (IS.PAID, IS.SHIPPING) for s in st):
        return PS.FOLLOW_UP
    return PS.SOURCING


def recompute(req: PurchaseRequest, actor: User, ip: str | None) -> None:
    if req.status in (PS.UNDER_REVIEW, PS.RETURNED, PS.VOID, PS.COMPLETED):
        if not (req.status == PS.UNDER_REVIEW and any(i.item_status in PROGRESSED for i in req.items)):
            return
    new = derive_status(req)
    if new == req.status:
        return
    old = req.status
    req.status = new
    if new == PS.COMPLETED:
        req.completed_at = _now()
    _ev(req, actor, from_status=old, to_status=new, note="محاسبهٔ خودکار از وضعیت اقلام")
    _audit(actor, req, "status_change", {"from": old.value, "to": new.value, "auto": True}, ip)


# ── pick lists ───────────────────────────────────────────────────────
def option_labels(kind: str, *, only_active: bool = True) -> list[str]:
    stmt = select(PurchaseOption.label).where(PurchaseOption.kind == kind)
    if only_active:
        stmt = stmt.where(PurchaseOption.is_active.is_(True))
    return list(db.session.scalars(stmt.order_by(PurchaseOption.sort_order, PurchaseOption.label)))


def meta(actor: User) -> dict:
    S.require_any(actor, S.READERS)
    sla = sla_map()
    return {
        "units": option_labels("UNIT"), "request_types": option_labels("REQUEST_TYPE"),
        "categories": [{"id": c.id, "name": c.name} for c in S.main_categories()],
        "request_statuses": [{"value": k, "label": v} for k, v in L.FLOW_STATUS.items()],
        "item_statuses": [{"value": k, "label": v} for k, v in L.ITEM_STATUS.items()],
        "priorities": [{"value": k, "label": v} for k, v in L.FLOW_PRIORITY.items()],
        "supply_places": [{"value": k, "label": v} for k, v in L.SUPPLY_PLACE.items()],
        "subjects": [{"value": k, "label": v} for k, v in L.SUBJECT.items()],
        "pay_methods": [{"value": k, "label": v} for k, v in L.PAY_METHOD.items()],
        "sla": [{"priority": k, "label": L.FLOW_PRIORITY[k], "amount": a, "unit": u} for k, (a, u) in sla.items()],
        "my_permissions": {**_mine(actor), "manage_catalog": S.can(actor, "manage_catalog")},
        "today": tehran_today().isoformat(),
        "currency": "IRR",
    }


def list_options(actor: User, kind: str | None) -> list[dict]:
    S.require_any(actor, ("settings",))
    stmt = select(PurchaseOption)
    if kind:
        stmt = stmt.where(PurchaseOption.kind == kind)
    rows = db.session.scalars(stmt.order_by(PurchaseOption.kind, PurchaseOption.sort_order, PurchaseOption.label)).all()
    used_units = dict(db.session.execute(select(PurchaseRequest.requester_unit, func.count()).where(
        PurchaseRequest.flow_version == 2).group_by(PurchaseRequest.requester_unit)).all())
    used_types = dict(db.session.execute(select(PurchaseItem.request_type, func.count()).where(
        PurchaseItem.request_type.is_not(None)).group_by(PurchaseItem.request_type)).all())
    return [{"id": r.id, "kind": r.kind, "label": r.label, "sort_order": r.sort_order, "is_active": r.is_active,
             "used_count": (used_units if r.kind == "UNIT" else used_types).get(r.label, 0)} for r in rows]


def _option_dict(r: PurchaseOption) -> dict:
    return {"id": r.id, "kind": r.kind, "label": r.label, "sort_order": r.sort_order, "is_active": r.is_active}


def create_option(actor: User, body: OptionIn, ip: str | None) -> dict:
    S.require(actor, "settings")
    S._need(body.kind in KINDS, "نوع فهرست معتبر نیست.", "kind")
    label = " ".join((body.label or "").split())
    S._need(label, "عنوان را وارد کنید.", "label")
    if db.session.scalar(select(PurchaseOption.id).where(PurchaseOption.kind == body.kind,
                                                         func.lower(PurchaseOption.label) == label.lower())):
        raise InvalidInputError("این گزینه قبلاً در فهرست وجود دارد.", "label")
    order = (db.session.scalar(select(func.max(PurchaseOption.sort_order)).where(PurchaseOption.kind == body.kind)) or 0) + 1
    row = PurchaseOption(kind=body.kind, label=label, sort_order=body.sort_order if body.sort_order is not None else order,
                         is_active=True if body.is_active is None else body.is_active)
    db.session.add(row)
    db.session.flush()
    write_audit_log(user_id=actor.id, action="create", module=S.MODULE, entity_type="purchase_option", entity_id=row.id,
                    metadata={"kind": row.kind, "label": label}, ip_address=ip)
    db.session.commit()
    return _option_dict(row)


def update_option(actor: User, option_id: int, body: OptionIn, ip: str | None) -> dict:
    S.require(actor, "settings")
    row = db.session.get(PurchaseOption, option_id)
    if row is None:
        raise NotFoundError("گزینه پیدا نشد.")
    before = _option_dict(row)
    data = body.model_dump(exclude_unset=True, exclude={"kind"})
    if "label" in data:
        label = " ".join((data["label"] or "").split())
        S._need(label, "عنوان را وارد کنید.", "label")
        clash = db.session.scalar(select(PurchaseOption.id).where(
            PurchaseOption.kind == row.kind, func.lower(PurchaseOption.label) == label.lower(), PurchaseOption.id != row.id))
        if clash:
            raise InvalidInputError("این گزینه قبلاً در فهرست وجود دارد.", "label")
        row.label = label   # old requests keep the text they were registered with
    if data.get("sort_order") is not None:
        row.sort_order = data["sort_order"]
    if data.get("is_active") is not None:
        row.is_active = data["is_active"]
    write_audit_log(user_id=actor.id, action="update", module=S.MODULE, entity_type="purchase_option", entity_id=row.id,
                    metadata={"before": before, "after": _option_dict(row)}, ip_address=ip)
    db.session.commit()
    return _option_dict(row)


def delete_option(actor: User, option_id: int, ip: str | None) -> None:
    S.require(actor, "settings")
    row = db.session.get(PurchaseOption, option_id)
    if row is None:
        raise NotFoundError("گزینه پیدا نشد.")
    used = (db.session.scalar(select(func.count()).select_from(PurchaseRequest).where(
        PurchaseRequest.flow_version == 2, PurchaseRequest.requester_unit == row.label)) if row.kind == "UNIT" else
        db.session.scalar(select(func.count()).select_from(PurchaseItem).where(PurchaseItem.request_type == row.label)))
    if used:
        raise ConflictError("این گزینه در درخواست‌ها استفاده شده است؛ به‌جای حذف، آن را غیرفعال کنید.")
    write_audit_log(user_id=actor.id, action="delete", module=S.MODULE, entity_type="purchase_option", entity_id=row.id,
                    metadata=_option_dict(row), ip_address=ip)
    db.session.delete(row)
    db.session.commit()


def save_sla(actor: User, body: SlaIn, ip: str | None) -> list[dict]:
    S.require(actor, "settings")
    seen = set()
    for r in body.rows:
        S._need(r.priority.value not in seen, "هر اولویت فقط یک بار قابل تنظیم است.", "rows")
        seen.add(r.priority.value)
        if r.unit == "HOURS":
            S._need(r.amount <= 24 * 365, "حداکثر زمان مجاز یک سال است.", "rows")
    existing = {r.priority: r for r in db.session.scalars(select(PurchaseSla))}
    before = {k: [v.amount, v.unit] for k, v in existing.items()}
    for r in body.rows:
        row = existing.get(r.priority.value)
        if row is None:
            row = PurchaseSla(priority=r.priority.value, amount=r.amount, unit=r.unit)
            db.session.add(row)
        else:
            row.amount, row.unit = r.amount, r.unit
        row.updated_by_name = (actor.full_name or "")[:200] or None
    write_audit_log(user_id=actor.id, action="update_sla", module=S.MODULE, entity_type="purchase_sla", entity_id=0,
                    metadata={"before": before, "after": {r.priority.value: [r.amount, r.unit] for r in body.rows}}, ip_address=ip)
    db.session.commit()
    return [{"priority": k, "label": L.FLOW_PRIORITY[k], "amount": a, "unit": u} for k, (a, u) in sla_map().items()]


# ── register / edit a request (warehouse) ────────────────────────────
def _check_unit(value: str | None) -> str:
    unit = " ".join((value or "").split())
    S._need(unit, "واحد متقاضی را انتخاب کنید.", "requester_unit")
    S._need(unit in option_labels("UNIT"), "واحد متقاضی باید از فهرست انتخاب شود.", "requester_unit")
    return unit


def _item_values(d: FlowItemIn, idx: int, old: PurchaseItem | None) -> dict:
    """Validated column values of one line. Name / group / unit come from the catalog product."""
    f = f"items.{idx}"
    product = None
    if d.product_id is not None:
        product = db.session.get(PurchaseProduct, d.product_id)
        S._need(product is not None and (product.is_active or (old is not None and old.product_id == product.id)),
                "کالا را از فهرست کالاها انتخاب کنید.", f"{f}.product_id")
    elif old is not None and old.product_id is not None:
        product = db.session.get(PurchaseProduct, old.product_id)
    S._need(product is not None or old is not None, "کالا را از فهرست کالاها انتخاب کنید.", f"{f}.product_id")

    cats = {c.id: c.name for c in S.main_categories()}
    category_id = product.category_id if product is not None and product.category_id in cats else d.category_id
    if category_id is None and old is not None and d.product_id is None:
        category_id = old.category_id
    S._need(category_id in cats, "گروه کالایی را انتخاب کنید.", f"{f}.category_id")

    unit = (product.unit if product is not None and product.unit else None) or " ".join((d.unit or "").split()) \
        or (old.unit if old is not None and d.product_id is None else None)
    S._need(unit, "واحد اندازه‌گیری را وارد کنید.", f"{f}.unit")
    S._need(len(unit) <= 40, "واحد اندازه‌گیری حداکثر ۴۰ نویسه است.", f"{f}.unit")

    S._need(d.quantity is not None, "مقدار درخواستی را وارد کنید.", f"{f}.quantity")
    S._need(d.current_stock is not None, "موجودی فعلی انبار را وارد کنید.", f"{f}.current_stock")
    types = option_labels("REQUEST_TYPE")
    S._need(d.request_type and (d.request_type in types or (old is not None and old.request_type == d.request_type)),
            "نوع درخواست را از فهرست انتخاب کنید.", f"{f}.request_type")
    S._need(d.purchase_subject is not None, "موضوع خرید را (دارایی یا عمومی) انتخاب کنید.", f"{f}.purchase_subject")
    S._need(d.priority is not None, "اولویت خرید را انتخاب کنید.", f"{f}.priority")
    return {
        "product": product, "category_id": category_id, "category_name": cats[category_id], "unit": unit,
        "quantity": d.quantity, "current_stock": d.current_stock, "reorder_point": d.reorder_point,
        "request_type": d.request_type, "purchase_subject": PurchaseSubject(d.purchase_subject), "priority": d.priority,
    }


def _apply_item(item: PurchaseItem, v: dict) -> None:
    p = v["product"]
    if p is not None:
        item.product_id, item.product_code, item.name = p.id, p.code, p.name
    item.category_id, item.category_name, item.unit = v["category_id"], v["category_name"], v["unit"]
    item.quantity, item.current_stock, item.reorder_point = v["quantity"], v["current_stock"], v["reorder_point"]
    item.request_type, item.purchase_subject, item.priority = v["request_type"], v["purchase_subject"], v["priority"]


def _check_head(body: FlowRequestIn) -> tuple[str, str, date]:
    unit = _check_unit(body.requester_unit)
    S._need(body.requester_name, "نام درخواست‌کننده را وارد کنید.", "requester_name")
    need = S._date(body.required_date, "required_date", label="تاریخ نیاز")
    S._need(need is not None, "تاریخ نیاز را وارد کنید.", "required_date")
    S._need(need >= tehran_today(), "تاریخ نیاز نمی‌تواند پیش از امروز باشد.", "required_date")
    return unit, body.requester_name, need


def create_request(actor: User, body: FlowRequestIn, ip: str | None = None) -> PurchaseRequest:
    S.require(actor, "warehouse")
    no = S._clean_request_no(body.request_no)
    S._check_request_no_free(no, None)
    unit, name, need = _check_head(body)
    S._need(body.items, "حداقل یک کالا به درخواست اضافه کنید.", "items")
    values = [_item_values(d, i, None) for i, d in enumerate(body.items)]
    now = _now()
    req = PurchaseRequest(
        request_no=no, status=PS.UNDER_REVIEW, flow_version=2, request_date=tehran_today(), submitted_at=now,
        requester_unit=unit, requester_name=name, required_date=need, current_step=1,
        review_status=ReviewStatus.PENDING_REVIEW, created_by_user_id=actor.id, updated_by_user_id=actor.id)
    db.session.add(req)
    db.session.flush()
    for pos, v in enumerate(values, start=1):
        item = PurchaseItem(request_id=req.id, position=pos, item_status=IS.PENDING)
        _apply_item(item, v)
        db.session.add(item)
    db.session.flush()
    _ev(req, actor, to_status=PS.UNDER_REVIEW, note="ثبت نهایی درخواست و ارجاع به کارتابل تدارکات")
    _audit(actor, req, "create", {"unit": unit, "items": len(values)}, ip)
    db.session.commit()
    return _load(req.id)


def update_request(actor: User, request_id: int, body: FlowRequestIn, ip: str | None = None) -> PurchaseRequest:
    """Only after procurement sent the request back («استرداد جهت اصلاح»); saving hands it back for review."""
    S.require(actor, "warehouse")
    req = _load(request_id)
    if req.status != PS.RETURNED:
        raise ConflictError("درخواست فقط پس از «استرداد جهت اصلاح» قابل ویرایش است.")
    if body.request_no is not None and " ".join(body.request_no.split()) != req.request_no:
        no = S._clean_request_no(body.request_no)
        S._check_request_no_free(no, req.id)
        req.request_no = no
    unit, name, need = _check_head(body)
    S._need(body.items, "حداقل یک کالا به درخواست اضافه کنید.", "items")
    existing = {i.id: i for i in req.items}
    keep = {d.id for d in body.items if d.id is not None}
    for iid, it in existing.items():
        if iid in keep:
            continue
        if it.quotes or it.item_status not in (IS.PENDING, IS.INQUIRY):
            raise ConflictError(f"کالای «{it.name}» دارای استعلام یا سابقهٔ بعدی است و حذف نمی‌شود.")
        db.session.delete(it)
    pos = 0
    for idx, d in enumerate(body.items):
        old = existing.get(d.id) if d.id is not None else None
        S._need(d.id is None or old is not None, "کالا در این درخواست پیدا نشد.", f"items.{idx}.id")
        if old is not None and (old.item_status == IS.CANCELLED or old.item_status in PROGRESSED):
            pos += 1          # a cancelled line (or one past the manager) is kept exactly as recorded
            old.position = pos
            continue
        if old is not None and old.quotes and d.product_id not in (None, old.product_id):
            raise ConflictError(f"کالای «{old.name}» استعلام دارد؛ نام کالا قابل تغییر نیست.")
        v = _item_values(d, idx, old)
        pos += 1
        if old is None:
            item = PurchaseItem(request_id=req.id, position=pos, item_status=IS.PENDING)
            db.session.add(item)
        else:
            item = old
            item.position = pos
            if item.item_status == IS.AWAITING_APPROVAL:   # data changed under the manager's eyes: decide again
                item.item_status = IS.INQUIRY
        _apply_item(item, v)
    req.requester_unit, req.requester_name, req.required_date = unit, name, need
    req.updated_by_user_id = actor.id
    req.status_note = None
    req.status = PS.UNDER_REVIEW
    db.session.flush()
    _ev(req, actor, from_status=PS.RETURNED, to_status=PS.UNDER_REVIEW, note="اصلاح و ارسال مجدد توسط انبار")
    _audit(actor, req, "resubmit", {"items": len(body.items)}, ip)
    db.session.commit()
    return _load(req.id)


# ── procurement: request status, supply place ────────────────────────
def set_status(actor: User, request_id: int, status: str, note: str | None, ip: str | None) -> PurchaseRequest:
    S.require(actor, "procure")
    req = _load(request_id)
    target = PS(status)
    if req.status in CLOSED_FLOW:
        raise ConflictError("این درخواست بسته شده است.")
    if any(i.item_status in PROGRESSED for i in req.items):
        raise ConflictError("پس از ارجاع کالاها به مالی، وضعیت کلی خودکار محاسبه می‌شود؛ برای هر کالا جداگانه اقدام کنید.")
    if target == req.status:
        return req
    if target in (PS.RETURNED, PS.VOID):
        S._need(note and note.strip(), "دلیل را بنویسید.", "note")
    old = req.status
    req.status = target
    req.status_note = note if target in (PS.RETURNED, PS.VOID) else None
    req.updated_by_user_id = actor.id
    if target == PS.SOURCING:
        for it in req.items:
            if it.item_status == IS.PENDING:
                it.item_status = IS.INQUIRY
                _ev(req, actor, item=it, kind="ITEM", from_status=IS.PENDING, to_status=IS.INQUIRY)
    elif target == PS.VOID:
        for it in req.items:
            if it.item_status != IS.CANCELLED:
                prev = it.item_status
                it.item_status, it.status_note = IS.CANCELLED, note
                _ev(req, actor, item=it, kind="ITEM", from_status=prev, to_status=IS.CANCELLED, note=note)
    _ev(req, actor, from_status=old, to_status=target, note=note)
    _audit(actor, req, "status_change", {"from": old.value, "to": target.value, "note": note}, ip)
    db.session.commit()
    return _load(req.id)


def set_supply_place(actor: User, request_id: int, item_id: int, place: str, ip: str | None) -> PurchaseRequest:
    S.require(actor, "procure")
    req = _load(request_id)
    it = _item(req, item_id)
    if it.item_status in (IS.DELIVERED, IS.CANCELLED) or req.status in CLOSED_FLOW:
        raise ConflictError("برای این کالا دیگر نمی‌توان محل تأمین را تغییر داد.")
    old = it.supply_place.value if it.supply_place else None
    it.supply_place = SupplyPlace(place)
    if old != place:
        _ev(req, actor, item=it, kind="ITEM", note=f"محل تأمین: {L.SUPPLY_PLACE[place]}")
        _audit(actor, req, "supply_place", {"item_id": it.id, "from": old, "to": place}, ip)
    db.session.commit()
    return _load(req.id)


# ── procurement: quotations of ONE item ──────────────────────────────
def _editable_quotes(req: PurchaseRequest, it: PurchaseItem) -> None:
    if req.status in CLOSED_FLOW or req.status in (PS.RETURNED,):
        raise ConflictError("این درخواست در وضعیتی است که استعلام آن قابل ثبت نیست.")
    if it.item_status not in QUOTE_EDITABLE:
        raise ConflictError("استعلام فقط در مرحلهٔ «در حال استعلام و تأمین» ثبت یا ویرایش می‌شود؛ پس از ارسال برای مدیر قفل است.")


def save_quote(actor: User, request_id: int, item_id: int, body: QuoteIn, ip: str | None) -> PurchaseRequest:
    S.require(actor, "procure")
    req = _load(request_id)
    it = _item(req, item_id)
    _editable_quotes(req, it)
    supplier = None
    if body.supplier_id is not None:
        supplier = db.session.get(Supplier, body.supplier_id)
        S._need(supplier is not None and supplier.deleted_at is None and supplier.is_active,
                "تأمین‌کنندهٔ انتخاب‌شده معتبر نیست.", "supplier_id")
    supplier_name = supplier.display_name if supplier is not None else " ".join((body.supplier_name or "").split())
    S._need(supplier_name, "نام تأمین‌کننده را وارد یا انتخاب کنید.", "supplier_name")
    S._need(body.unit_price is not None and body.unit_price > 0, "قیمت پیشنهادی را (به ریال) وارد کنید.", "unit_price")
    S._need(body.payment_method is not None, "روش پرداخت (نقدی یا چکی) را مشخص کنید.", "payment_method")
    received = S._date(body.received_date, "received_date", label="تاریخ استعلام") or tehran_today()
    f = _claim_file(actor, req, body.file_id, "file_id", "پیوست استعلام")
    if body.id is not None:
        q = next((x for x in it.quotes if x.id == body.id), None)
        S._need(q is not None, "استعلام پیدا نشد.", "id")
        before = {"supplier": q.supplier_name, "unit_price": S.num(q.unit_price)}
    else:
        q = PurchaseItemQuote(item_id=it.id, position=len(it.quotes) + 1,
                              created_by_name=(actor.full_name or "")[:200] or None)
        it.quotes.append(q)
        before = None
    q.supplier_id, q.supplier_name, q.unit_price = (supplier.id if supplier else None), supplier_name, body.unit_price
    q.received_date, q.validity_days, q.delivery_days = received, body.validity_days, body.delivery_days
    q.payment_method, q.payment_terms, q.note = PayMethod(body.payment_method), body.payment_terms, body.note
    if f is not None:
        q.file_id = f.id
    db.session.flush()
    _ev(req, actor, item=it, kind="ITEM", note=f"{'ویرایش' if before else 'ثبت'} استعلام «{supplier_name}»")
    _audit(actor, req, "quote_update" if before else "quote_create",
           {"item_id": it.id, "supplier": supplier_name, "unit_price": S.num(body.unit_price), "before": before}, ip)
    db.session.commit()
    return _load(req.id)


def delete_quote(actor: User, request_id: int, item_id: int, quote_id: int, ip: str | None) -> PurchaseRequest:
    S.require(actor, "procure")
    req = _load(request_id)
    it = _item(req, item_id)
    _editable_quotes(req, it)
    q = next((x for x in it.quotes if x.id == quote_id), None)
    if q is None:
        raise NotFoundError("استعلام پیدا نشد.")
    _ev(req, actor, item=it, kind="ITEM", note=f"حذف استعلام «{q.supplier_name}»")
    _audit(actor, req, "quote_delete", {"item_id": it.id, "supplier": q.supplier_name, "unit_price": S.num(q.unit_price)}, ip)
    it.quotes.remove(q)
    db.session.commit()
    return _load(req.id)


def submit_to_manager(actor: User, request_id: int, item_ids: list[int], ip: str | None) -> PurchaseRequest:
    S.require(actor, "procure")
    req = _load(request_id)
    if req.status in CLOSED_FLOW or req.status == PS.RETURNED:
        raise ConflictError("این درخواست در وضعیتی است که قابل ارسال برای مدیر نیست.")
    for iid in dict.fromkeys(item_ids):
        it = _item(req, iid)
        S._need(it.item_status == IS.INQUIRY, f"کالای «{it.name}» در مرحلهٔ استعلام نیست.", "item_ids")
        S._need(it.quotes, f"برای کالای «{it.name}» هنوز استعلامی ثبت نشده است.", "item_ids")
        S._need(it.supply_place is not None, f"محل تأمین (محلی / غیرمحلی) کالای «{it.name}» را مشخص کنید.", "item_ids")
        it.item_status = IS.AWAITING_APPROVAL
        _ev(req, actor, item=it, kind="ITEM", from_status=IS.INQUIRY, to_status=IS.AWAITING_APPROVAL, note="ارسال برای تأیید مدیر")
        _audit(actor, req, "item_status", {"item_id": it.id, "to": IS.AWAITING_APPROVAL.value}, ip)
    recompute(req, actor, ip)
    db.session.commit()
    return _load(req.id)


# ── manager ──────────────────────────────────────────────────────────
def manager_decide(actor: User, request_id: int, item_id: int, body: ManagerDecisionIn, ip: str | None) -> PurchaseRequest:
    S.require(actor, "manager")
    req = _load(request_id)
    it = _item(req, item_id)
    if it.item_status != IS.AWAITING_APPROVAL:
        raise ConflictError("این کالا در انتظار تأیید مدیر نیست.")
    who = (actor.full_name or "")[:200] or None
    if body.action == "RETURN":
        S._need(body.note and body.note.strip(), "دلیل بازگشت به تدارکات را بنویسید.", "note")
        it.item_status, it.manager_note, it.status_note, it.selected_quote_id = IS.INQUIRY, body.note, body.note, None
        _ev(req, actor, item=it, kind="ITEM", from_status=IS.AWAITING_APPROVAL, to_status=IS.INQUIRY,
            note=f"بازگشت از مدیر: {body.note}")
        _audit(actor, req, "manager_return", {"item_id": it.id, "note": body.note}, ip)
    else:
        q = next((x for x in it.quotes if x.id == body.quote_id), None)
        S._need(q is not None, "یکی از استعلام‌های همین کالا را برای تأیید انتخاب کنید.", "quote_id")
        lowest = min(S._dec(x.unit_price) for x in it.quotes)
        if S._dec(q.unit_price) > lowest:
            S._need(body.note and body.note.strip(), "گزینهٔ انتخاب‌شده ارزان‌ترین نیست؛ دلیل انتخاب را بنویسید.", "note")
        it.selected_quote_id, it.manager_note = q.id, body.note
        it.approved_at, it.approved_by_name, it.status_note = _now(), who, None
        it.item_status = IS.IN_FINANCE
        _ev(req, actor, item=it, kind="ITEM", from_status=IS.AWAITING_APPROVAL, to_status=IS.IN_FINANCE,
            note=f"تأیید مدیر: {q.supplier_name}")
        _audit(actor, req, "manager_approve", {"item_id": it.id, "quote_id": q.id, "supplier": q.supplier_name,
                                               "unit_price": S.num(q.unit_price), "note": body.note}, ip)
    recompute(req, actor, ip)
    db.session.commit()
    return _load(req.id)


# ── finance ──────────────────────────────────────────────────────────
def _selected_quote(it: PurchaseItem) -> PurchaseItemQuote | None:
    return next((q for q in it.quotes if q.id == it.selected_quote_id), None)


def record_payment(actor: User, request_id: int, item_id: int, body: PaymentIn, ip: str | None) -> PurchaseRequest:
    S.require(actor, "finance")
    req = _load(request_id)
    it = _item(req, item_id)
    if it.item_status != IS.IN_FINANCE:
        raise ConflictError("این کالا برای پرداخت به مالی ارجاع نشده است.")
    if it.payment is not None:
        raise ConflictError("پرداخت این کالا قبلاً ثبت شده و قابل بازنویسی نیست.")
    quote = _selected_quote(it)
    method = PayMethod(body.method) if body.method else (quote.payment_method if quote else None)
    S._need(method is not None, "روش پرداخت را مشخص کنید.", "method")
    expected = None if quote is None else S._dec(quote.unit_price) * S._dec(it.quantity)
    pay = PurchaseItemPayment(item_id=it.id, quote_id=quote.id if quote else None, method=method,
                              recorded_by_name=(actor.full_name or "")[:200] or None, note=body.note)
    if method == PayMethod.CASH:
        pay.paid_date = S._date(body.paid_date, "paid_date", label="تاریخ پرداخت")
        S._need(pay.paid_date is not None, "تاریخ پرداخت را وارد کنید.", "paid_date")
        S._need(body.payment_ref, "شناسه پرداخت را وارد کنید.", "payment_ref")
        f = _claim_file(actor, req, body.receipt_file_id, "receipt_file_id", "رسید پرداخت")
        S._need(f is not None, "تصویر یا فایل رسید پرداخت را بارگذاری کنید.", "receipt_file_id")
        pay.payment_ref, pay.receipt_file_id = body.payment_ref, f.id
        pay.amount = body.amount if body.amount is not None else expected
    else:
        f = _claim_file(actor, req, body.cheque_file_id, "cheque_file_id", "تصویر چک")
        S._need(f is not None, "تصویر چک را بارگذاری کنید.", "cheque_file_id")
        S._need(body.cheque_no, "شمارهٔ چک را وارد کنید.", "cheque_no")
        S._need(body.cheque_amount is not None and body.cheque_amount > 0, "مبلغ چک را وارد کنید.", "cheque_amount")
        issue = S._date(body.cheque_issue_date, "cheque_issue_date", label="تاریخ صدور")
        due = S._date(body.cheque_due_date, "cheque_due_date", label="تاریخ سررسید")
        S._need(issue is not None, "تاریخ صدور چک را وارد کنید.", "cheque_issue_date")
        S._need(due is not None, "تاریخ سررسید چک را وارد کنید.", "cheque_due_date")
        S._need(due >= issue, "تاریخ سررسید نمی‌تواند پیش از تاریخ صدور باشد.", "cheque_due_date")
        pay.cheque_file_id, pay.cheque_no, pay.cheque_amount = f.id, body.cheque_no, body.cheque_amount
        pay.cheque_issue_date, pay.cheque_due_date = issue, due
        pay.cheque_bank, pay.cheque_payee = body.cheque_bank, body.cheque_payee
        pay.amount = body.cheque_amount
    it.payment = pay
    db.session.flush()
    _ev(req, actor, item=it, kind="ITEM", note=f"ثبت پرداخت {L.PAY_METHOD[method.value]}")
    _audit(actor, req, "payment_recorded", {"item_id": it.id, "method": method.value, "amount": S.num(pay.amount)}, ip)
    db.session.commit()
    return _load(req.id)


def finance_return(actor: User, request_id: int, body: FinanceReturnIn, ip: str | None) -> PurchaseRequest:
    """Finance hands the paid items back to procurement (they become «پرداخت‌شده»)."""
    S.require(actor, "finance")
    req = _load(request_id)
    pool = [i for i in req.items if i.item_status == IS.IN_FINANCE]
    if body.item_ids is not None:
        pool = [i for i in pool if i.id in set(body.item_ids)]
    S._need(pool, "کالایی برای ارجاع به تدارکات وجود ندارد.", "item_ids")
    unpaid = [i.name for i in pool if i.payment is None]
    if body.item_ids is not None:
        S._need(not unpaid, "برای این کالاها هنوز پرداخت ثبت نشده است: " + "، ".join(unpaid), "item_ids")
    ready = [i for i in pool if i.payment is not None]
    S._need(ready, "ابتدا اطلاعات پرداخت را ثبت کنید.", "item_ids")
    now = _now()
    for it in ready:
        it.item_status, it.paid_at = IS.PAID, now
        _ev(req, actor, item=it, kind="ITEM", from_status=IS.IN_FINANCE, to_status=IS.PAID, note="ارجاع به تدارکات پس از پرداخت")
        _audit(actor, req, "item_status", {"item_id": it.id, "to": IS.PAID.value}, ip)
    recompute(req, actor, ip)
    db.session.commit()
    return _load(req.id)


# ── procurement / warehouse: shipping and delivery ───────────────────
def set_item_status(actor: User, request_id: int, item_id: int, body: ItemStatusIn, ip: str | None) -> PurchaseRequest:
    req = _load(request_id)
    it = _item(req, item_id)
    target = IS(body.status)
    old = it.item_status
    S.require_any(actor, ("warehouse", "procure") if target == IS.DELIVERED else ("procure",))
    if req.status in CLOSED_FLOW:
        raise ConflictError("این درخواست بسته شده است.")
    if target == IS.SHIPPING:
        S._need(old == IS.PAID, "فقط کالای «پرداخت‌شده» به وضعیت «در حال حمل» می‌رود.", "status")
        it.shipped_at = _now()
    elif target == IS.DELIVERED:
        S._need(old in (IS.PAID, IS.SHIPPING), "کالا باید ابتدا پرداخت شده باشد تا «تحویل داده‌شده» ثبت شود.", "status")
        it.delivered_at, it.delivered_by_name = _now(), (actor.full_name or "")[:200] or None
        if body.file_id:
            _set_receipt(actor, req, it, body.file_id)
    elif target == IS.CANCELLED:
        S._need(old in (IS.PENDING, IS.INQUIRY, IS.AWAITING_APPROVAL, IS.IN_FINANCE),
                "کالایی که پرداخت و برگشت از مالی شده یا تحویل شده، قابل ابطال نیست.", "status")
        S._need(it.payment is None, "برای این کالا پرداخت ثبت شده و قابل ابطال نیست.", "status")
        S._need(body.note and body.note.strip(), "دلیل ابطال را بنویسید.", "note")
        it.status_note = body.note
    it.item_status = target
    _ev(req, actor, item=it, kind="ITEM", from_status=old, to_status=target, note=body.note)
    _audit(actor, req, "item_status", {"item_id": it.id, "from": old.value, "to": target.value, "note": body.note}, ip)
    recompute(req, actor, ip)
    db.session.commit()
    return _load(req.id)


def _set_receipt(actor: User, req: PurchaseRequest, it: PurchaseItem, file_id: str) -> None:
    if it.receipt_file_id:
        raise ConflictError("رسید انبار این کالا قبلاً ثبت شده و قابل بازنویسی نیست.")
    f = _claim_file(actor, req, file_id, "file_id", "رسید انبار")
    it.receipt_file_id, it.receipt_uploaded_at = f.id, _now()


def upload_receipt(actor: User, request_id: int, item_id: int, file_id: str, ip: str | None) -> PurchaseRequest:
    S.require_any(actor, ("warehouse", "procure"))
    req = _load(request_id)
    it = _item(req, item_id)
    S._need(it.item_status == IS.DELIVERED, "رسید انبار فقط برای کالای «تحویل داده‌شده» ثبت می‌شود.", "status")
    _set_receipt(actor, req, it, file_id)
    _ev(req, actor, item=it, kind="ITEM", note="بارگذاری رسید انبار")
    _audit(actor, req, "receipt_uploaded", {"item_id": it.id}, ip)
    db.session.commit()
    return _load(req.id)


# ── serialization ────────────────────────────────────────────────────
def _file(f):
    return {"id": f.id, "name": f.original_name, "size": f.size} if f is not None else None


def quote_dict(it: PurchaseItem, q: PurchaseItemQuote, lowest) -> dict:
    total = S._dec(q.unit_price) * S._dec(it.quantity)
    return {
        "id": q.id, "position": q.position, "supplier_id": q.supplier_id, "supplier_name": q.supplier_name,
        "unit_price": S.num(q.unit_price), "total_price": S.num(total),
        "received_date": _d(q.received_date), "received_date_jalali": _j(q.received_date),
        "validity_days": q.validity_days, "delivery_days": q.delivery_days,
        "payment_method": q.payment_method.value if q.payment_method else None,
        "payment_method_label": L.PAY_METHOD.get(q.payment_method.value) if q.payment_method else None,
        "payment_terms": q.payment_terms, "note": q.note, "file": _file(q.file),
        "is_lowest": lowest is not None and S._dec(q.unit_price) == lowest, "is_selected": q.id == it.selected_quote_id,
    }


def payment_dict(p: PurchaseItemPayment | None) -> dict | None:
    if p is None:
        return None
    return {
        "id": p.id, "method": p.method.value, "method_label": L.PAY_METHOD[p.method.value], "amount": S.num(p.amount),
        "paid_date": _d(p.paid_date), "paid_date_jalali": _j(p.paid_date), "payment_ref": p.payment_ref,
        "receipt_file": _file(p.receipt_file), "cheque_file": _file(p.cheque_file), "cheque_no": p.cheque_no,
        "cheque_amount": S.num(p.cheque_amount), "cheque_issue_date": _d(p.cheque_issue_date),
        "cheque_issue_date_jalali": _j(p.cheque_issue_date), "cheque_due_date": _d(p.cheque_due_date),
        "cheque_due_date_jalali": _j(p.cheque_due_date), "cheque_bank": p.cheque_bank, "cheque_payee": p.cheque_payee,
        "note": p.note, "recorded_by_name": p.recorded_by_name, "recorded_at": _stamp(p.created_at),
    }


def item_dict(actor: User, req: PurchaseRequest, it: PurchaseItem, sla: dict, now: datetime) -> dict:
    m = _mine(actor)
    money = _money_visible(actor, it)
    open_req = req.status not in CLOSED_FLOW and req.status != PS.RETURNED
    lowest = min((S._dec(q.unit_price) for q in it.quotes), default=None)
    sel = _selected_quote(it)
    t = timing(req, it, sla, now)
    out = {
        "id": it.id, "position": it.position, "product_id": it.product_id, "product_code": it.product_code,
        "name": it.name, "category_id": it.category_id, "category_name": it.category_name, "unit": it.unit,
        "quantity": S.num(it.quantity), "current_stock": S.num(it.current_stock), "reorder_point": S.num(it.reorder_point),
        "request_type": it.request_type,
        "purchase_subject": it.purchase_subject.value if it.purchase_subject else None,
        "purchase_subject_label": L.SUBJECT.get(it.purchase_subject.value) if it.purchase_subject else None,
        "priority": it.priority.value if it.priority else None,
        "priority_label": L.FLOW_PRIORITY.get(it.priority.value) if it.priority else None,
        "status": it.item_status.value, "status_label": L.ITEM_STATUS[it.item_status.value], "status_note": it.status_note,
        "supply_place": it.supply_place.value if it.supply_place else None,
        "supply_place_label": L.SUPPLY_PLACE.get(it.supply_place.value) if it.supply_place else None,
        "quotes_count": len(it.quotes),
        "approved_at": _stamp(it.approved_at), "approved_by_name": it.approved_by_name, "manager_note": it.manager_note,
        "paid_at": _stamp(it.paid_at), "shipped_at": _stamp(it.shipped_at), "delivered_at": _stamp(it.delivered_at),
        "delivered_by_name": it.delivered_by_name,
        "has_payment": it.payment is not None,
        "receipt": _file(it.receipt_file), "receipt_uploaded_at": _stamp(it.receipt_uploaded_at),
        "receipt_missing": it.item_status == IS.DELIVERED and it.receipt_file_id is None,
        "timing": t,
        "can": {
            "set_supply_place": m["procure"] and it.item_status not in (IS.DELIVERED, IS.CANCELLED) and open_req,
            "edit_quotes": m["procure"] and it.item_status in QUOTE_EDITABLE and open_req,
            "submit_to_manager": m["procure"] and it.item_status == IS.INQUIRY and open_req and bool(it.quotes),
            "decide": m["manager"] and it.item_status == IS.AWAITING_APPROVAL,
            "pay": m["finance"] and it.item_status == IS.IN_FINANCE and it.payment is None,
            "ship": m["procure"] and it.item_status == IS.PAID,
            "deliver": (m["procure"] or m["warehouse"]) and it.item_status in (IS.PAID, IS.SHIPPING),
            "upload_receipt": (m["procure"] or m["warehouse"]) and it.item_status == IS.DELIVERED and it.receipt_file_id is None,
            "cancel": m["procure"] and it.item_status in (IS.PENDING, IS.INQUIRY, IS.AWAITING_APPROVAL, IS.IN_FINANCE)
            and it.payment is None and req.status not in CLOSED_FLOW,
        },
    }
    if money:
        out["quotes"] = [quote_dict(it, q, lowest) for q in it.quotes]
        out["selected_quote_id"] = it.selected_quote_id
        out["selected_total"] = S.num(S._dec(sel.unit_price) * S._dec(it.quantity)) if sel else None
        out["payment_method"] = (sel.payment_method.value if sel and sel.payment_method else None)
        out["payment"] = payment_dict(it.payment)
    return out


def events_for(req: PurchaseRequest) -> list[dict]:
    names = {i.id: i.name for i in req.items}
    rows = db.session.scalars(select(PurchaseEvent).where(PurchaseEvent.request_id == req.id)
                              .order_by(PurchaseEvent.created_at, PurchaseEvent.id)).all()
    out = []
    for e in rows:
        labels = L.ITEM_STATUS if e.item_id else {**L.STATUS, **L.FLOW_STATUS}
        out.append({
            "id": e.id, "scope": "ITEM" if e.item_id else "REQUEST", "item_id": e.item_id,
            "item_name": names.get(e.item_id), "from_status": e.from_status, "to_status": e.to_status,
            "from_label": labels.get(e.from_status) if e.from_status else None,
            "to_label": labels.get(e.to_status) if e.to_status else None,
            "note": e.note, "user_name": e.user_name, "at": _stamp(e.created_at)})
    return out


def counts(req: PurchaseRequest) -> dict:
    c = {s.value: 0 for s in IS}
    for i in req.items:
        c[i.item_status.value] += 1
    return c


def request_dict(actor: User, req: PurchaseRequest, *, detail: bool = True) -> dict:
    sla, now = sla_map(), _now()
    m = _mine(actor)
    c = counts(req)
    active = [i for i in req.items if i.item_status != IS.CANCELLED]
    items = [item_dict(actor, req, i, sla, now) for i in req.items]
    if m["finance"] and not (m["read"] or m["warehouse"] or m["procure"] or m["manager"]):
        items = [i for i in items if i["status"] in {s.value for s in PROGRESSED}]
    data = {
        "id": req.id, "request_no": req.request_no, "status": req.status.value,
        "status_label": L.FLOW_STATUS.get(req.status.value, L.STATUS.get(req.status.value)), "status_note": req.status_note,
        "requester_unit": req.requester_unit, "requester_name": req.requester_name,
        "request_date": _d(req.request_date), "request_date_jalali": _j(req.request_date),
        "required_date": _d(req.required_date), "required_date_jalali": _j(req.required_date),
        "submitted_at": _stamp(req.submitted_at), "creator_name": req.creator_name or req.creator_display,
        "items_count": len(active), "counts": c,
        "awaiting_manager": c["AWAITING_APPROVAL"], "in_finance": c["IN_FINANCE"],
        "missing_receipts": sum(1 for i in req.items if i.item_status == IS.DELIVERED and i.receipt_file_id is None),
        "overdue_items": sum(1 for i in items if i["timing"] and i["timing"]["overdue"]),
        "items": items,
        "my_actions": {
            "can_edit": m["warehouse"] and req.status == PS.RETURNED,
            "can_set_status": m["procure"] and req.status not in CLOSED_FLOW
            and not any(i.item_status in PROGRESSED for i in req.items),
            "can_finance_return": m["finance"] and any(i.item_status == IS.IN_FINANCE and i.payment is not None for i in req.items),
            **{k: v for k, v in m.items()},
        },
    }
    if detail:
        data["events"] = events_for(req)
    return data


# ── lists ────────────────────────────────────────────────────────────
def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"


def list_requests(actor: User, args, page: int, per_page: int) -> tuple[list[dict], int]:
    S.require_any(actor, S.READERS)
    m = _mine(actor)
    finance_only = m["finance"] and not (m["read"] or m["warehouse"] or m["procure"] or m["manager"])
    stmt = _stmt()
    queue = args.get("queue")
    prog = [s for s in PROGRESSED]
    if queue == "manager":
        S.require(actor, "manager")
        stmt = stmt.where(exists().where(PurchaseItem.request_id == PurchaseRequest.id, PurchaseItem.item_status == IS.AWAITING_APPROVAL))
    elif queue == "finance":
        S.require(actor, "finance")
        stmt = stmt.where(exists().where(PurchaseItem.request_id == PurchaseRequest.id, PurchaseItem.item_status == IS.IN_FINANCE))
    elif queue == "finance_done":
        S.require(actor, "finance")
        stmt = stmt.where(exists().where(PurchaseItem.request_id == PurchaseRequest.id, PurchaseItem.item_status.in_([IS.PAID, IS.SHIPPING, IS.DELIVERED])))
    elif finance_only:
        stmt = stmt.where(exists().where(PurchaseItem.request_id == PurchaseRequest.id, PurchaseItem.item_status.in_(prog)))
    elif queue == "open":
        stmt = stmt.where(PurchaseRequest.status.not_in([PS.COMPLETED, PS.VOID]))
    if args.get("status"):
        stmt = stmt.where(PurchaseRequest.status.in_([PS(s) for s in args["status"].split(",") if s in PS.__members__]))
    if args.get("item_status") in IS.__members__:
        stmt = stmt.where(exists().where(PurchaseItem.request_id == PurchaseRequest.id,
                                         PurchaseItem.item_status == IS(args["item_status"])))
    if args.get("unit"):
        stmt = stmt.where(PurchaseRequest.requester_unit == args["unit"])
    q = (args.get("q") or "").strip()[:80]
    if q:
        like = _like(q)
        stmt = stmt.where(PurchaseRequest.request_no.like(like, escape="\\") | PurchaseRequest.requester_name.like(like, escape="\\")
                          | exists().where(PurchaseItem.request_id == PurchaseRequest.id, PurchaseItem.name.like(like, escape="\\")))
    total = db.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.session.scalars(
        stmt.options(selectinload(PurchaseRequest.items).selectinload(PurchaseItem.payment),
                     selectinload(PurchaseRequest.items).selectinload(PurchaseItem.quotes))
        .order_by(PurchaseRequest.created_at.desc(), PurchaseRequest.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    out = []
    for r in rows:
        d = request_dict(actor, r, detail=False)
        d["items"] = [{k: i[k] for k in ("id", "name", "status", "status_label", "priority", "priority_label", "supply_place_label",
                                         "receipt_missing", "has_payment", "quantity", "unit")}
                      | {"overdue": bool(i["timing"] and i["timing"]["overdue"])} for i in d["items"]]
        out.append(d)
    return out, total


# ── KPIs ─────────────────────────────────────────────────────────────
def _filters(args):
    d1 = S._date(args.get("date_from"), "date_from", label="از تاریخ")
    d2 = S._date(args.get("date_to"), "date_to", label="تا تاریخ")
    pr = args.get("priority")
    S._need(pr in (None, "", *L.FLOW_PRIORITY), "اولویت معتبر نیست.", "priority")
    return d1, d2, args.get("unit") or None, pr or None


def _bucket() -> dict:
    return {"items": 0, "requests": set(), "delivered": 0, "on_time": 0, "late": 0, "open": 0, "open_overdue": 0,
            "delay_sum": 0.0, "elapsed_sum": 0.0}


def _finish(b: dict) -> dict:
    due = b["delivered"] + b["open_overdue"]          # items whose time has come: delivered, or open and already late
    return {
        "items": b["items"], "requests": len(b["requests"]), "delivered": b["delivered"], "delivered_on_time": b["on_time"],
        "delivered_late": b["late"], "open": b["open"], "open_overdue": b["open_overdue"], "open_in_time": b["open"] - b["open_overdue"],
        "attainment_pct": round(b["on_time"] * 100 / due, 1) if due else None,
        "avg_delay_hours": round(b["delay_sum"] / (b["late"] + b["open_overdue"]), 1) if (b["late"] + b["open_overdue"]) else 0.0,
        "avg_elapsed_hours_delivered": round(b["elapsed_sum"] / b["delivered"], 1) if b["delivered"] else None,
    }


def kpi_rows(actor: User, args) -> tuple[dict, list[dict]]:
    S.require_any(actor, ("read", "procure", "manager"))
    d1, d2, unit, pr = _filters(args)
    stmt = _stmt().options(selectinload(PurchaseRequest.items))
    if d1:
        stmt = stmt.where(PurchaseRequest.request_date >= d1)
    if d2:
        stmt = stmt.where(PurchaseRequest.request_date <= d2)
    if unit:
        stmt = stmt.where(PurchaseRequest.requester_unit == unit)
    sla, now = sla_map(), _now()
    overall = _bucket()
    by_pr = {k: _bucket() for k in L.FLOW_PRIORITY}
    rows = []
    for req in db.session.scalars(stmt):
        for it in req.items:
            p = (it.priority or PurchasePriority.NORMAL).value
            if pr and p != pr:
                continue
            t = timing(req, it, sla, now)
            if t is None:
                continue
            for b in (overall, by_pr[p]):
                b["items"] += 1
                b["requests"].add(req.id)
                if t["delivered"]:
                    b["delivered"] += 1
                    b["elapsed_sum"] += t["elapsed_hours"]
                    if t["on_time"]:
                        b["on_time"] += 1
                    else:
                        b["late"] += 1
                        b["delay_sum"] += t["delay_hours"]
                else:
                    b["open"] += 1
                    if t["overdue"]:
                        b["open_overdue"] += 1
                        b["delay_sum"] += t["delay_hours"]
            rows.append({
                "request_id": req.id, "request_no": req.request_no, "requester_unit": req.requester_unit,
                "item_id": it.id, "item_name": it.name, "priority": p, "priority_label": L.FLOW_PRIORITY[p],
                "status": it.item_status.value, "status_label": L.ITEM_STATUS[it.item_status.value],
                "request_date_jalali": _j(req.request_date), "deadline": t["deadline"],
                "delivered_at": _stamp(it.delivered_at), "elapsed_hours": t["elapsed_hours"],
                "remaining_hours": t["remaining_hours"], "delay_hours": t["delay_hours"],
                "state": ("ON_TIME" if t["on_time"] else "LATE") if t["delivered"] else ("OVERDUE" if t["overdue"] else "OPEN"),
            })
    order = {"OVERDUE": 0, "LATE": 1, "OPEN": 2, "ON_TIME": 3}
    rows.sort(key=lambda r: (order[r["state"]], -r["delay_hours"], r["request_no"]))
    summary = {
        "overall": _finish(overall),
        "by_priority": [{"priority": k, "label": L.FLOW_PRIORITY[k], **_finish(v)} for k, v in by_pr.items()],
        "sla": [{"priority": k, "label": L.FLOW_PRIORITY[k], "amount": a, "unit": u, "unit_label": L.SLA_UNIT[u]}
                for k, (a, u) in sla.items()],
    }
    return summary, rows


def kpi(actor: User, args) -> dict:
    summary, rows = kpi_rows(actor, args)
    limit = min(max(int(args.get("limit") or 300), 1), 2000)
    return {**summary, "rows": rows[:limit], "rows_total": len(rows)}


def kpi_export(actor: User, args) -> tuple[str, list[str], list[list]]:
    S.require(actor, "export")
    _, rows = kpi_rows(actor, args)
    headers = ["شماره درخواست", "واحد متقاضی", "کالا", "اولویت", "وضعیت کالا", "تاریخ ثبت", "موعد تحویل", "تاریخ تحویل",
               "زمان سپری‌شده (ساعت)", "زمان باقی‌مانده (ساعت)", "میزان تأخیر (ساعت)", "نتیجه"]
    labels = {"ON_TIME": "تحویل در موعد", "LATE": "تحویل با تأخیر", "OVERDUE": "دارای تأخیر", "OPEN": "در مهلت"}
    body = [[r["request_no"], r["requester_unit"], r["item_name"], r["priority_label"], r["status_label"],
             r["request_date_jalali"], r["deadline"], r["delivered_at"], r["elapsed_hours"], r["remaining_hours"],
             r["delay_hours"], labels[r["state"]]] for r in rows]
    return "گزارش زمان‌بندی تأمین", headers, body
