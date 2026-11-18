"""
Service layer for /api/purchases -- permission checks, wizard steps, workflow and audit.

Access: every function checks `procurement.purchase.<action>` GLOBALLY (same decision as Suppliers and
Logistics: no department scoping). Actions: read / create / update / delete, plus the non-CRUD extras
`approve` (approve a reference price, send a request back for revision, reopen a closed one) and
`export`. The checks live HERE, so hiding a button in the front end is never the only protection.

Workflow (status) in short:
    DRAFT -> ENTERING (step 1 completed) -> AWAITING_INQUIRY (submit: steps 1-3 complete)
          -> INQUIRING (first quotation) -> AWAITING_SELECTION (quotations finalized)
          -> PURCHASING (supplier selected) -> AWAITING_DELIVERY (purchase recorded, not fully delivered)
          -> COMPLETED (fully delivered)
    any open status -> CANCELLED (reason) ; open/closed -> NEEDS_REVISION (approve permission, reason)
Every status change and every saved step is written to `purchase_events` (who / when) and the important
ones to the shared audit log.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.audit_logs.services import write_audit_log
from app.core.departments.models import Department
from app.core.users.models import User
from app.extensions import db
from app.modules.purchases.models import (
    DeliveryStatus, PurchaseEvent, PurchaseFile, PurchaseInquiry, PurchaseInquiryItem, PurchaseItem,
    PurchasePriority, PurchaseProduct, PurchaseRequest, PurchaseStatus, ReferenceSource, ReviewStatus,
)
from app.modules.purchases.schemas import (
    ApproveReferenceIn, BasicIn, BudgetIn, InquiriesIn, ItemsIn, ResultIn, SelectionIn,
)
from app.modules.suppliers.models import Supplier, SupplierCategory, SupplierStatus
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError
import re

from app.utils.jalali import parse_date_input, tehran_today

MODULE = "procurement"
ENTITY = "purchase_request"
ZERO = Decimal("0")
MAX_INQUIRIES = 3
MAX_FILES = 10
CLOSED = (PurchaseStatus.COMPLETED, PurchaseStatus.CANCELLED)
# item add / remove is only possible while no quotation depends on the item list
STRUCTURE_OPEN = (PurchaseStatus.DRAFT, PurchaseStatus.ENTERING, PurchaseStatus.AWAITING_INQUIRY, PurchaseStatus.NEEDS_REVISION)


# ── permissions ──────────────────────────────────────────────────────
def _key(action: str) -> str:
    return f"procurement.purchase.{action}"


def require(actor: User, action: str) -> None:
    if not has_permission(actor, _key(action), None, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{_key(action)}' for this action.")


def can(actor: User, action: str) -> bool:
    return has_permission(actor, _key(action), None, None)


def viewer_flags(actor: User, req: PurchaseRequest) -> dict:
    open_ = req.status not in CLOSED
    return {
        "can_edit": can(actor, "update") and open_ and req.review_status != ReviewStatus.REJECTED,
        "can_cancel": can(actor, "update") and open_,
        "can_delete": can(actor, "delete") and req.status in (PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED),
        "can_approve": can(actor, "approve"),
        "can_send_back": can(actor, "approve") and req.status != PurchaseStatus.DRAFT,
        "can_reopen": can(actor, "approve") and not open_,
        "can_send_to_finance": can(actor, "update") and req.status == PurchaseStatus.PURCHASING,
        "can_manage_catalog": can(actor, "manage_catalog"),
        "can_review": can(actor, "update"),
        "can_export": can(actor, "export"),
    }


# ── small helpers ────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def num(value):
    """Decimal/None -> int | float | None for JSON."""
    if value is None:
        return None
    d = Decimal(value)
    return int(d) if d == d.to_integral_value() else float(d)


def _dec(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _date(value, field: str, *, label: str) -> date | None:
    if value in (None, ""):
        return None
    try:
        return parse_date_input(value)
    except (ValueError, TypeError):
        raise InvalidInputError(f"«{label}» معتبر نیست.", field) from None


def _need(cond, message: str, field: str) -> None:
    if not cond:
        raise InvalidInputError(message, field)


def _audit(actor: User, req: PurchaseRequest, action: str, meta: dict | None, ip: str | None) -> None:
    write_audit_log(user_id=actor.id, action=action, module=MODULE, entity_type=ENTITY, entity_id=req.id,
                    metadata={"request_no": req.request_no, **(meta or {})}, ip_address=ip)


def _event(req: PurchaseRequest, actor: User, kind: str, *, step: str | None = None, from_status=None,
           to_status=None, note: str | None = None) -> None:
    db.session.add(PurchaseEvent(
        request_id=req.id, kind=kind, step=step, from_status=getattr(from_status, "value", from_status),
        to_status=getattr(to_status, "value", to_status), note=note, user_id=actor.id,
        user_name=(actor.full_name or "")[:200] or None, created_at=_now(),
    ))


def _set_status(req: PurchaseRequest, new: PurchaseStatus, actor: User, ip: str | None, note: str | None = None) -> None:
    old = req.status
    if old == new:
        return
    req.status = new
    _event(req, actor, "STATUS", from_status=old, to_status=new, note=note)
    _audit(actor, req, "status_change", {"from": old.value, "to": new.value, "note": note}, ip)


def _touch(req: PurchaseRequest, actor: User, step: str, ip: str | None) -> None:
    req.updated_by_user_id = actor.id
    order = ["basic", "items", "budget", "inquiries", "selection", "result"]
    req.current_step = max(req.current_step or 1, order.index(step) + 1)
    _event(req, actor, "STEP", step=step)


# ── loading ──────────────────────────────────────────────────────────
def _load(request_id: int) -> PurchaseRequest:
    req = db.session.scalars(
        select(PurchaseRequest).where(PurchaseRequest.id == request_id, PurchaseRequest.deleted_at.is_(None))
        .options(
            selectinload(PurchaseRequest.items),
            selectinload(PurchaseRequest.inquiries).selectinload(PurchaseInquiry.lines),
            selectinload(PurchaseRequest.inquiries).selectinload(PurchaseInquiry.file),
        )
    ).first()
    if req is None:
        raise NotFoundError("درخواست خرید پیدا نشد.")
    return req


def get_request(actor: User, request_id: int) -> PurchaseRequest:
    require(actor, "read")
    return _load(request_id)


def _editable(actor: User, request_id: int) -> PurchaseRequest:
    require(actor, "update")
    req = _load(request_id)
    if req.status in CLOSED:
        raise ConflictError("این درخواست بسته شده است؛ برای ویرایش، مدیر باید آن را برای اصلاح بازگرداند.")
    if req.review_status == ReviewStatus.REJECTED:
        raise ConflictError("این درخواست «رد شده» است و در سوابق می‌ماند؛ برای ادامهٔ کار، ابتدا وضعیت بررسی آن را تغییر دهید.")
    return req


# ── totals ───────────────────────────────────────────────────────────
def estimated_total(req: PurchaseRequest) -> Decimal | None:
    """Sum of qty x estimated unit price; None unless EVERY item carries an estimate."""
    if not req.items or any(i.estimated_unit_price is None for i in req.items):
        return None
    return sum((_dec(i.quantity) * _dec(i.estimated_unit_price) for i in req.items), ZERO)


def inquiry_lines_complete(req: PurchaseRequest, inq: PurchaseInquiry) -> bool:
    priced = {ln.item_id for ln in inq.lines}
    return bool(req.items) and all(i.id in priced for i in req.items)


def recompute_inquiry(req: PurchaseRequest, inq: PurchaseInquiry) -> None:
    qty = {i.id: _dec(i.quantity) for i in req.items}
    items_total = sum((qty.get(ln.item_id, ZERO) * _dec(ln.unit_price) for ln in inq.lines), ZERO)
    inq.total_price = items_total + (_dec(inq.extra_costs) or ZERO)


def lowest_inquiry_total(req: PurchaseRequest) -> Decimal | None:
    totals = [_dec(q.total_price) for q in req.inquiries if inquiry_lines_complete(req, q)]
    return min(totals) if totals else None


def item_savings(item: PurchaseItem) -> Decimal | None:
    """(reference - final unit price) x purchased quantity -- ONLY against an approved reference price."""
    if (item.reference_unit_price is None or item.reference_approved_at is None
            or item.final_unit_price is None or item.purchased_quantity is None):
        return None
    return (_dec(item.reference_unit_price) - _dec(item.final_unit_price)) * _dec(item.purchased_quantity)


def recompute_final(req: PurchaseRequest) -> None:
    if req.purchase_date is None and not any(i.purchased_quantity is not None for i in req.items):
        req.final_amount = None
        return
    lines = sum((_dec(i.final_unit_price or 0) * _dec(i.purchased_quantity or 0) for i in req.items), ZERO)
    req.final_amount = lines + (_dec(req.final_extra_costs) or ZERO)


# ── files ────────────────────────────────────────────────────────────
def _file_refs(rows) -> list[dict]:
    return [{"id": r.id, "name": r.original_name, "size": r.size} for r in rows]


def _attach_files(actor: User, req: PurchaseRequest, refs) -> list[dict]:
    ids = list(dict.fromkeys(r.id for r in (refs or [])))
    if len(ids) > MAX_FILES:
        raise InvalidInputError(f"حداکثر {MAX_FILES} فایل مجاز است.", "files")
    if not ids:
        return []
    rows = db.session.scalars(select(PurchaseFile).where(PurchaseFile.id.in_(ids))).all()
    found = {r.id: r for r in rows}
    for fid in ids:
        row = found.get(fid)
        mine = row is not None and (row.request_id == req.id or (row.request_id is None and row.uploaded_by_user_id == actor.id))
        if not mine:
            raise InvalidInputError("فایل پیوست معتبر نیست؛ آن را دوباره بارگذاری کنید.", "files")
        row.request_id = req.id
    return _file_refs(found[i] for i in ids)


# ── request number (typed by the expert -- the system never numbers requests) ──
REQUEST_NO_RE = re.compile(r"^[\w\-./\\+#()\[\] ]+$", re.UNICODE)


def _clean_request_no(value: str | None) -> str:
    no = " ".join((value or "").split())
    _need(no, "شماره درخواست را وارد کنید.", "request_no")
    _need(len(no) <= 30, "شماره درخواست حداکثر ۳۰ نویسه است.", "request_no")
    _need(REQUEST_NO_RE.match(no), "شماره درخواست فقط می‌تواند شامل حروف، عدد و - _ . / \\ + # ( ) [ ] باشد.", "request_no")
    return no


def _check_request_no_free(no: str, exclude_id: int | None) -> None:
    q = select(PurchaseRequest.id).where(func.lower(PurchaseRequest.request_no) == no.lower())  # soft-deleted rows count too
    if exclude_id is not None:
        q = q.where(PurchaseRequest.id != exclude_id)
    if db.session.scalar(q) is not None:
        raise InvalidInputError("این شماره درخواست قبلاً ثبت شده است.", "request_no")


# ── meta ─────────────────────────────────────────────────────────────
def main_categories() -> list[SupplierCategory]:
    """The commodity groups: the admin-managed MAIN categories of the supplier bank (nothing is hardcoded)."""
    return list(db.session.scalars(
        select(SupplierCategory).where(SupplierCategory.parent_id.is_(None), SupplierCategory.is_active.is_(True))
        .order_by(SupplierCategory.sort_order, SupplierCategory.name)
    ))


def meta(actor: User) -> dict:
    require(actor, "read")
    from app.modules.purchases import labels as L

    units = db.session.scalars(select(PurchaseItem.unit).group_by(PurchaseItem.unit).order_by(func.count().desc()).limit(30)).all()
    requester_units = set(db.session.scalars(select(Department.name).where(Department.deleted_at.is_(None), Department.is_active.is_(True))))
    requester_units |= set(db.session.scalars(
        select(PurchaseRequest.requester_unit).where(PurchaseRequest.requester_unit.is_not(None)).distinct().limit(200)))
    return {
        "categories": [{"id": c.id, "name": c.name} for c in main_categories()],
        "units": list(units),
        "requester_units": sorted(u for u in requester_units if u),
        "statuses": [{"value": k, "label": v} for k, v in L.STATUS.items()],
        "priorities": [{"value": k, "label": v} for k, v in L.PRIORITY.items()],
        "review_statuses": [{"value": k, "label": v} for k, v in L.REVIEW.items()],
        "delivery_statuses": [{"value": k, "label": v} for k, v in L.DELIVERY.items()],
        "reference_sources": [{"value": k, "label": v} for k, v in L.REFERENCE_SOURCE.items()],
        "selection_reasons": [{"value": k, "label": v} for k, v in L.SELECTION_REASON.items()],
        "steps": [{"value": k, "label": v} for k, v in L.STEP.items()],
        "max_inquiries": MAX_INQUIRIES,
        "currency": "IRR",
        "my_permissions": {a: can(actor, a) for a in ("read", "create", "update", "delete", "approve", "export", "manage_catalog")},
    }


def search_suppliers(actor: User, q: str | None, limit: int = 20) -> list[dict]:
    """Suppliers from the supplier bank that may be quoted (not inactive / removed)."""
    require(actor, "read")
    stmt = select(Supplier).where(Supplier.deleted_at.is_(None), Supplier.is_active.is_(True),
                                  Supplier.status != SupplierStatus.INACTIVE)
    if q and q.strip():
        like = f"%{q.strip()[:80]}%"
        stmt = stmt.where(
            Supplier.company_name.like(like) | Supplier.first_name.like(like)
            | Supplier.last_name.like(like) | Supplier.brand_name.like(like)
        )
    rows = db.session.scalars(stmt.order_by(Supplier.company_name, Supplier.last_name).limit(min(max(limit, 1), 50))).all()
    return [{"id": s.id, "name": s.display_name, "category": s.category} for s in rows]


# ── create / step 1 ──────────────────────────────────────────────────
def create_request(actor: User, body: BasicIn, ip: str | None = None) -> PurchaseRequest:
    require(actor, "create")
    no = _clean_request_no(body.request_no)
    _check_request_no_free(no, None)
    req = PurchaseRequest(
        request_no=no, status=PurchaseStatus.DRAFT, created_by_user_id=actor.id, updated_by_user_id=actor.id,
        request_date=tehran_today(), priority=PurchasePriority.NORMAL, current_step=1,
        review_status=ReviewStatus.PENDING_REVIEW,
    )
    _apply_basic(req, body)
    try:
        with db.session.begin_nested():
            db.session.add(req)
            db.session.flush()
    except IntegrityError:
        raise InvalidInputError("این شماره درخواست قبلاً ثبت شده است.", "request_no") from None
    _event(req, actor, "STATUS", to_status=PurchaseStatus.DRAFT, note="ثبت درخواست")
    _touch(req, actor, "basic", ip)
    _audit(actor, req, "create", {"subject": req.subject, "unit": req.requester_unit}, ip)
    if body.complete:
        _validate_basic(req)
        _set_status(req, PurchaseStatus.ENTERING, actor, ip)
    db.session.commit()
    return _load(req.id)


def _apply_basic(req: PurchaseRequest, body: BasicIn) -> None:
    data = body.model_dump(exclude_unset=True, exclude={"complete", "request_no"})
    if "request_date" in data:
        req.request_date = _date(data.pop("request_date"), "request_date", label="تاریخ ثبت") or req.request_date
    for k, v in data.items():
        setattr(req, k, v)


def _validate_basic(req: PurchaseRequest) -> None:
    _need(req.requester_unit, "نام شرکت یا واحد متقاضی را وارد کنید.", "requester_unit")
    _need(req.requester_name, "نام درخواست‌کننده را وارد کنید.", "requester_name")
    _need(req.request_date, "تاریخ ثبت را وارد کنید.", "request_date")
    _need(req.subject, "موضوع خرید را وارد کنید.", "subject")
    _need(req.reason, "علت و ضرورت خرید را وارد کنید.", "reason")


def save_basic(actor: User, request_id: int, body: BasicIn, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    before = {"subject": req.subject, "priority": req.priority.value, "request_no": req.request_no}
    if body.request_no is not None and " ".join(body.request_no.split()) != req.request_no:
        no = _clean_request_no(body.request_no)
        _check_request_no_free(no, req.id)
        req.request_no = no
    _apply_basic(req, body)
    if body.complete:
        _validate_basic(req)
        if req.status == PurchaseStatus.DRAFT:
            _set_status(req, PurchaseStatus.ENTERING, actor, ip)
    _touch(req, actor, "basic", ip)
    after = {"subject": req.subject, "priority": req.priority.value, "request_no": req.request_no}
    if before != after:
        _audit(actor, req, "update_basic", {"before": before, "after": after}, ip)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise InvalidInputError("این شماره درخواست قبلاً ثبت شده است.", "request_no") from None
    return _load(req.id)


# ── step 2: items ────────────────────────────────────────────────────
def _item_prices(req: PurchaseRequest) -> dict:
    return {i.id: [num(i.quantity), num(i.estimated_unit_price), num(i.reference_unit_price), num(i.final_unit_price)] for i in req.items}


def save_items(actor: User, request_id: int, body: ItemsIn, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    cats = {c.id: c.name for c in main_categories()}
    existing = {i.id: i for i in req.items}
    rows = []
    for idx, raw in enumerate(body.items):
        d = raw.model_dump()
        if not any(d.get(k) for k in ("category_id", "name", "quantity", "unit", "specs", "brand_model")):
            continue  # an untouched blank row
        f = f"items.{idx}"
        _need(d["category_id"] in cats, "گروه کالایی را از فهرست انتخاب کنید.", f"{f}.category_id")
        old = existing.get(d["id"]) if d["id"] is not None else None
        if d["product_id"] is not None:
            prod = db.session.get(PurchaseProduct, d["product_id"])
            _need(prod is not None and (prod.is_active or (old is not None and old.product_id == prod.id)),
                  "کالا را از فهرست کالاهای ثبت‌شده انتخاب کنید.", f"{f}.product_id")
            d["name"], d["_code"] = prod.name, prod.code
        elif old is not None:  # an item already in the request keeps its catalog link (or its legacy free-text name)
            d["product_id"], d["_code"] = old.product_id, old.product_code
            d["name"] = old.name if old.product_id else d["name"]
        else:
            raise InvalidInputError("کالا را از فهرست کالاهای ثبت‌شده انتخاب کنید.", f"{f}.product_id")
        _need(d["name"], "نام کالا را وارد کنید.", f"{f}.name")
        _need(d["quantity"] is not None and d["quantity"] > 0, "تعداد باید بزرگ‌تر از صفر باشد.", f"{f}.quantity")
        d["unit"] = " ".join((d["unit"] or "").split())  # free text, only whitespace is tidied
        _need(d["unit"], "واحد اندازه‌گیری را وارد کنید.", f"{f}.unit")
        if d["id"] is not None:
            _need(d["id"] in existing, "قلم کالا در این درخواست پیدا نشد.", f"{f}.id")
        rows.append((idx, d))
    if body.complete:
        _need(rows, "حداقل یک قلم کالا ثبت کنید.", "items")

    new_ids = {d["id"] for _, d in rows if d["id"] is not None}
    structure_changed = bool(set(existing) - new_ids) or any(d["id"] is None for _, d in rows)
    if structure_changed and req.inquiries:
        raise ConflictError("پس از ثبت استعلام، افزودن یا حذف قلم ممکن نیست؛ ابتدا استعلام‌ها را حذف یا اصلاح کنید.")
    if structure_changed and req.status not in STRUCTURE_OPEN:
        raise ConflictError("در وضعیت فعلی، افزودن یا حذف قلم ممکن نیست.")

    before = _item_prices(req)
    for item in [i for i in req.items if i.id not in new_ids]:
        req.items.remove(item)
    for pos, (idx, d) in enumerate(rows, start=1):
        item = existing.get(d["id"]) if d["id"] is not None else None
        if item is None:
            item = PurchaseItem(category_name="", name="", quantity=ZERO, unit="")
            req.items.append(item)
        item.position = pos
        item.category_id = d["category_id"]
        item.category_name = cats[d["category_id"]]
        item.product_id, item.product_code = d["product_id"], d.get("_code")
        item.name, item.specs, item.brand_model = d["name"], d["specs"], d["brand_model"]
        item.quantity, item.unit = d["quantity"], d["unit"]
        item.estimated_unit_price = d["estimated_unit_price"]
        _apply_reference(req, item, d, f"items.{idx}")
    db.session.flush()
    for inq in req.inquiries:  # quantities may have changed
        recompute_inquiry(req, inq)
    if req.purchase_date:
        recompute_final(req)
    _touch(req, actor, "items", ip)
    after = _item_prices(req)
    if before != after:
        _audit(actor, req, "update_items", {"before": before, "after": after}, ip)
    db.session.commit()
    return _load(req.id)


def _apply_reference(req: PurchaseRequest, item: PurchaseItem, d: dict, field: str) -> None:
    """A reference price is PROPOSED here and counts only after someone with `approve` approves it."""
    src, price, note, ref_id = d["reference_source"], d["reference_unit_price"], d["reference_note"], d["reference_item_id"]
    if src is None and price is None and not note and ref_id is None:
        changed = item.reference_unit_price is not None
        item.reference_unit_price = item.reference_source = item.reference_note = item.reference_item_id = None
        if changed:
            item.reference_approved_at = item.reference_approved_by_user_id = None
        return
    _need(src is not None, "منبع قیمت مبنا را انتخاب کنید.", f"{field}.reference_source")
    if src == ReferenceSource.LAST_PURCHASE:
        _need(ref_id is not None, "قلم خرید قبلی را برای قیمت مبنا مشخص کنید.", f"{field}.reference_item_id")
        prev = db.session.get(PurchaseItem, ref_id)
        done = prev is not None and prev.request_id != req.id and prev.final_unit_price is not None \
            and db.session.get(PurchaseRequest, prev.request_id).status == PurchaseStatus.COMPLETED
        _need(done, "قلم انتخاب‌شده، خرید تکمیل‌شدهٔ قبلی با قیمت نهایی نیست.", f"{field}.reference_item_id")
        price = prev.final_unit_price  # taken from the record itself so it can be traced, never typed in
    else:
        _need(price is not None, "قیمت مبنا را وارد کنید.", f"{field}.reference_unit_price")
        _need(note, "مستند یا توضیح منبع قیمت مبنا را بنویسید تا قابل ردیابی باشد.", f"{field}.reference_note")
        ref_id = None
    unchanged = (_dec(price) == _dec(item.reference_unit_price) and src == item.reference_source
                 and (note or None) == item.reference_note and ref_id == item.reference_item_id)
    item.reference_unit_price, item.reference_source = price, src
    item.reference_note, item.reference_item_id = note, ref_id
    if not unchanged:
        item.reference_approved_at = item.reference_approved_by_user_id = None


def approve_reference(actor: User, request_id: int, body: ApproveReferenceIn, ip: str | None = None) -> PurchaseRequest:
    """Confirm the reference unit prices of the given items (needs `procurement.purchase.approve`)."""
    require(actor, "approve")
    req = _load(request_id)
    by_id = {i.id: i for i in req.items}
    for iid in body.item_ids:
        item = by_id.get(iid)
        _need(item is not None, "قلم کالا در این درخواست پیدا نشد.", "item_ids")
        _need(item.reference_unit_price is not None, f"برای «{item.name}» قیمت مبنا ثبت نشده است.", "item_ids")
        item.reference_approved_by_user_id, item.reference_approved_at = actor.id, _now()
    _event(req, actor, "REFERENCE", note=f"{len(body.item_ids)} قلم")
    _audit(actor, req, "approve_reference_price", {"items": {i: num(by_id[i].reference_unit_price) for i in body.item_ids}}, ip)
    db.session.commit()
    return _load(req.id)


# ── step 3: budget ───────────────────────────────────────────────────
def save_budget(actor: User, request_id: int, body: BudgetIn, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    data = body.model_dump(exclude_unset=True, exclude={"complete", "files"})
    before = {"budget_amount": num(req.budget_amount)}
    if "required_date" in data:
        req.required_date = _date(data.pop("required_date"), "required_date", label="تاریخ موردنیاز")
    for k, v in data.items():
        setattr(req, k, v)
    if body.files is not None:
        req.budget_files = _attach_files(actor, req, body.files)
    if body.complete:
        _need(req.required_date, "تاریخ موردنیاز را وارد کنید.", "required_date")
        _need(req.delivery_location, "محل تحویل را وارد کنید.", "delivery_location")
        _need(req.budget_amount is not None or estimated_total(req) is not None,
              "بودجه پیش‌بینی‌شده یا قیمت تخمینی همهٔ اقلام را وارد کنید.", "budget_amount")
    _touch(req, actor, "budget", ip)
    after = {"budget_amount": num(req.budget_amount)}
    if before != after:
        _audit(actor, req, "update_budget", {"before": before, "after": after}, ip)
    db.session.commit()
    return _load(req.id)


def submit(actor: User, request_id: int, ip: str | None = None) -> PurchaseRequest:
    """Steps 1-3 are done: the request goes on to the quotation stage (also used to resubmit after a revision)."""
    req = _editable(actor, request_id)
    _validate_basic(req)
    _need(req.items, "حداقل یک قلم کالا ثبت کنید.", "items")
    _need(req.required_date and req.delivery_location, "تاریخ موردنیاز و محل تحویل را در مرحلهٔ بودجه وارد کنید.", "budget")
    _need(req.budget_amount is not None or estimated_total(req) is not None,
          "بودجه پیش‌بینی‌شده یا قیمت تخمینی همهٔ اقلام را وارد کنید.", "budget_amount")
    new = pipeline_status(req)
    _set_status(req, new, actor, ip, note="ارسال به مرحلهٔ بعد")
    if new == PurchaseStatus.COMPLETED:
        req.completed_at = req.completed_at or _now()
    db.session.commit()
    return _load(req.id)


def pipeline_status(req: PurchaseRequest) -> PurchaseStatus:
    """The status that matches how far the recorded data has got."""
    if req.purchase_date is not None and req.delivery_status == DeliveryStatus.DELIVERED and req.final_amount is not None:
        return PurchaseStatus.COMPLETED
    if req.purchase_date is not None:
        return PurchaseStatus.AWAITING_DELIVERY
    if req.selected_inquiry_id is not None and req.sent_to_finance_at is not None:
        return PurchaseStatus.SENT_TO_FINANCE
    if req.selected_inquiry_id is not None:
        return PurchaseStatus.PURCHASING
    if req.inquiries_finalized_at is not None and req.inquiries:
        return PurchaseStatus.AWAITING_SELECTION
    if req.inquiries:
        return PurchaseStatus.INQUIRING
    return PurchaseStatus.AWAITING_INQUIRY


# ── step 4: inquiries ────────────────────────────────────────────────
def save_inquiries(actor: User, request_id: int, body: InquiriesIn, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    _need(req.items, "ابتدا اقلام کالا را ثبت کنید.", "inquiries")
    _need(req.status not in (PurchaseStatus.DRAFT, PurchaseStatus.ENTERING),
          "ابتدا مراحل اول تا سوم را تکمیل و ارسال کنید.", "inquiries")
    if len(body.inquiries) > MAX_INQUIRIES:
        raise InvalidInputError(f"حداکثر {MAX_INQUIRIES} استعلام مجاز است.", "inquiries")

    item_ids = {i.id for i in req.items}
    supplier_ids = [q.supplier_id for q in body.inquiries]
    _need(all(supplier_ids), "تأمین‌کننده را از بانک تأمین‌کنندگان انتخاب کنید.", "inquiries")
    _need(len(set(supplier_ids)) == len(supplier_ids), "یک تأمین‌کننده را نمی‌توان دو بار استعلام گرفت.", "inquiries")
    suppliers = {s.id: s for s in db.session.scalars(select(Supplier).where(Supplier.id.in_(supplier_ids), Supplier.deleted_at.is_(None)))} if supplier_ids else {}

    parsed = []
    for idx, q in enumerate(body.inquiries):
        f = f"inquiries.{idx}"
        sup = suppliers.get(q.supplier_id)
        _need(sup is not None, "تأمین‌کنندهٔ انتخاب‌شده در بانک تأمین‌کنندگان پیدا نشد.", f"{f}.supplier_id")
        received = _date(q.received_date, f"{f}.received_date", label="تاریخ دریافت استعلام")
        _need(received, "تاریخ دریافت استعلام را وارد کنید.", f"{f}.received_date")
        prices = {}
        for ln in q.lines:
            _need(ln.item_id in item_ids, "قلم کالا در این درخواست پیدا نشد.", f"{f}.lines")
            prices[ln.item_id] = ln.unit_price
        if body.complete:
            _need(set(prices) == item_ids, "برای همهٔ اقلام قیمت پیشنهادی را وارد کنید.", f"{f}.lines")
            _need(q.validity_days is not None, "مدت اعتبار پیشنهاد را وارد کنید.", f"{f}.validity_days")
            _need(q.delivery_days is not None, "زمان تحویل را وارد کنید.", f"{f}.delivery_days")
            _need(q.payment_terms, "شرایط پرداخت را وارد کنید.", f"{f}.payment_terms")
        parsed.append((q, sup, received, prices))
    if body.complete:
        _need(parsed, "حداقل یک استعلام ثبت کنید.", "inquiries")
        if len(parsed) < MAX_INQUIRIES:
            _need(body.shortfall_reason, "علت عدم امکان اخذ سه استعلام را بنویسید.", "shortfall_reason")

    _need(req.purchase_date is None, "پس از ثبت خرید، استعلام‌ها قابل تغییر نیستند؛ درخواست باید برای اصلاح بازگردانده شود.", "inquiries")
    _need(req.sent_to_finance_at is None or req.status == PurchaseStatus.NEEDS_REVISION,
          "پس از ارسال به مالی، استعلام‌ها قابل تغییر نیستند؛ درخواست باید برای اصلاح بازگردانده شود.", "inquiries")
    before = {q.supplier_id: num(q.total_price) for q in req.inquiries}
    selected_before = next((num(q.total_price) for q in req.inquiries if q.id == req.selected_inquiry_id), None)
    by_supplier = {q.supplier_id: q for q in req.inquiries}
    keep = {q.supplier_id for q, *_ in parsed}
    selected_removed = False
    for inq in [q for q in req.inquiries if q.supplier_id not in keep]:
        selected_removed |= inq.id == req.selected_inquiry_id
        req.inquiries.remove(inq)
    if selected_removed:
        _clear_selection(req)
    db.session.flush()
    free = [p for p in range(1, MAX_INQUIRIES + 1) if p not in {q.position for q in req.inquiries}]
    for q, sup, received, prices in parsed:
        inq = by_supplier.get(q.supplier_id)
        if inq is None:
            inq = PurchaseInquiry(position=free.pop(0), supplier_id=sup.id, supplier_name=sup.display_name,
                                  received_date=received, total_price=ZERO)
            req.inquiries.append(inq)
        inq.received_date, inq.validity_days, inq.delivery_days = received, q.validity_days, q.delivery_days
        inq.payment_terms, inq.extra_costs, inq.note = q.payment_terms, q.extra_costs, q.note
        if q.file_id:
            f = db.session.get(PurchaseFile, q.file_id)
            ok = f is not None and (f.request_id == req.id or (f.request_id is None and f.uploaded_by_user_id == actor.id))
            _need(ok, "فایل پیش‌فاکتور معتبر نیست.", "inquiries")
            f.request_id = req.id
        inq.file_id = q.file_id
        if inq.id is not None:
            inq.lines.clear()
            db.session.flush()  # old rows go first: (inquiry, item) is unique
        inq.lines.extend(PurchaseInquiryItem(item_id=i, unit_price=p) for i, p in prices.items())
    db.session.flush()
    for inq in req.inquiries:
        recompute_inquiry(req, inq)
    req.inquiry_shortfall_reason = body.shortfall_reason
    if selected_before is not None and req.selected_inquiry_id is not None:
        sel = next((q for q in req.inquiries if q.id == req.selected_inquiry_id), None)
        if sel is None or num(sel.total_price) != selected_before:
            _clear_selection(req)  # the chosen quotation was re-priced: the supplier must be chosen again
    _touch(req, actor, "inquiries", ip)
    after = {q.supplier_id: num(q.total_price) for q in req.inquiries}
    if before != after:
        _audit(actor, req, "update_inquiries", {"before": before, "after": after}, ip)

    if body.complete:
        req.inquiries_finalized_at = req.inquiries_finalized_at or _now()
    elif not req.inquiries:
        req.inquiries_finalized_at = None
    if req.status in (PurchaseStatus.AWAITING_INQUIRY, PurchaseStatus.INQUIRING, PurchaseStatus.AWAITING_SELECTION,
                      PurchaseStatus.PURCHASING, PurchaseStatus.SENT_TO_FINANCE):
        _set_status(req, pipeline_status(req), actor, ip)
    db.session.commit()
    return _load(req.id)


def _clear_selection(req: PurchaseRequest) -> None:
    req.selected_inquiry_id = None
    req.selection_reasons = None
    req.selection_note = None
    req.sent_to_finance_at = None
    for i in req.items:
        i.final_unit_price = None


# ── step 5: selection ────────────────────────────────────────────────
def save_selection(actor: User, request_id: int, body: SelectionIn, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    _need(req.inquiries, "ابتدا استعلام‌ها را ثبت کنید.", "inquiry_id")
    _need(req.inquiries_finalized_at is not None or req.status in (PurchaseStatus.PURCHASING, PurchaseStatus.AWAITING_DELIVERY, PurchaseStatus.NEEDS_REVISION),
          "ابتدا مرحلهٔ استعلام را نهایی کنید.", "inquiry_id")
    _need(req.sent_to_finance_at is None or req.status == PurchaseStatus.NEEDS_REVISION,
          "پس از ارسال به مالی، انتخاب تأمین‌کننده قابل تغییر نیست؛ درخواست باید برای اصلاح بازگردانده شود.", "inquiry_id")
    inq = next((q for q in req.inquiries if q.id == body.inquiry_id), None)
    _need(inq is not None, "تأمین‌کنندهٔ برنده را از میان استعلام‌های ثبت‌شده انتخاب کنید.", "inquiry_id")
    _need(inquiry_lines_complete(req, inq), "استعلام انتخاب‌شده برای همهٔ اقلام قیمت ندارد.", "inquiry_id")

    quoted = {ln.item_id: _dec(ln.unit_price) for ln in inq.lines}
    agreed = {ln.item_id: ln.final_unit_price for ln in body.lines}
    _need(set(agreed) <= set(quoted), "قلم کالا در این درخواست پیدا نشد.", "lines")
    lowest = lowest_inquiry_total(req)
    not_lowest = lowest is not None and _dec(inq.total_price) > lowest
    if body.complete:
        _need(body.reasons, "علت انتخاب تأمین‌کننده را مشخص کنید.", "reasons")
        if not_lowest:
            _need(body.note, "تأمین‌کنندهٔ انتخابی کمترین قیمت را نداده است؛ توضیح انتخاب الزامی است.", "note")
        if "OTHER" in body.reasons:
            _need(body.note, "برای «سایر موارد» توضیح بنویسید.", "note")

    before = {"inquiry": req.selected_inquiry_id, "prices": {i.id: num(i.final_unit_price) for i in req.items}}
    req.sent_to_finance_at = None  # a changed selection / price has to go to finance again
    req.selected_inquiry_id = inq.id
    req.selection_reasons = list(body.reasons)
    req.selection_note = body.note
    for item in req.items:
        item.final_unit_price = agreed.get(item.id, quoted[item.id])
    if req.purchase_date:
        recompute_final(req)  # prices were re-agreed after the purchase was recorded
    after = {"inquiry": req.selected_inquiry_id, "prices": {i.id: num(i.final_unit_price) for i in req.items}}
    _touch(req, actor, "selection", ip)
    _audit(actor, req, "select_supplier", {
        "supplier": inq.supplier_name, "not_lowest_price": bool(not_lowest), "reasons": list(body.reasons),
        "before": before, "after": after}, ip)
    if body.complete and req.status in (PurchaseStatus.AWAITING_SELECTION, PurchaseStatus.INQUIRING):
        _set_status(req, PurchaseStatus.PURCHASING, actor, ip)
    db.session.commit()
    return _load(req.id)


# ── step 6: result ───────────────────────────────────────────────────
def save_result(actor: User, request_id: int, body: ResultIn, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    _need(req.selected_inquiry_id is not None, "ابتدا تأمین‌کنندهٔ برنده را انتخاب کنید.", "purchase_date")
    by_id = {i.id: i for i in req.items}
    lines = {ln.item_id: ln for ln in body.lines}
    _need(set(lines) <= set(by_id), "قلم کالا در این درخواست پیدا نشد.", "lines")
    purchase_date = _date(body.purchase_date, "purchase_date", label="تاریخ انجام خرید")
    if body.complete:
        _need(req.sent_to_finance_at is not None, "ابتدا درخواست را «ارسال به مالی» کنید.", "purchase_date")
        _need(purchase_date, "تاریخ انجام خرید را وارد کنید.", "purchase_date")
        _need(body.delivery_status is not None, "وضعیت تحویل کالا را مشخص کنید.", "delivery_status")
        _need(set(lines) == set(by_id), "مقدار خریداری‌شدهٔ همهٔ اقلام را وارد کنید.", "lines")

    before = {"final_amount": num(req.final_amount), "delivery": req.delivery_status.value}
    req.purchase_date = purchase_date
    req.final_extra_costs = body.final_extra_costs
    req.completion_note = body.completion_note
    if body.delivery_status is not None:
        req.delivery_status = body.delivery_status
    if body.files is not None:
        req.final_files = _attach_files(actor, req, body.files)
    for iid, ln in lines.items():
        by_id[iid].purchased_quantity = ln.purchased_quantity
        if ln.final_unit_price is not None:
            by_id[iid].final_unit_price = ln.final_unit_price
    recompute_final(req)
    _touch(req, actor, "result", ip)
    _audit(actor, req, "update_result", {
        "before": before, "after": {"final_amount": num(req.final_amount), "delivery": req.delivery_status.value},
        "prices": {i.id: num(i.final_unit_price) for i in req.items}}, ip)
    if body.complete:
        done = pipeline_status(req)
        _set_status(req, done, actor, ip)
        if done == PurchaseStatus.COMPLETED:
            req.completed_at = _now()
    db.session.commit()
    return _load(req.id)


# ── workflow actions ─────────────────────────────────────────────────
def send_to_finance(actor: User, request_id: int, ip: str | None = None) -> PurchaseRequest:
    """The selected supplier / agreed prices are final: hand the purchase to finance (ارسال به مالی)."""
    req = _editable(actor, request_id)
    _need(req.status == PurchaseStatus.PURCHASING and req.selected_inquiry_id is not None,
          "ابتدا تأمین‌کنندهٔ برنده را انتخاب و ثبت کنید.", "status")
    _need(all(i.final_unit_price is not None for i in req.items), "قیمت توافقی همهٔ اقلام باید ثبت شده باشد.", "status")
    req.sent_to_finance_at = _now()
    _set_status(req, PurchaseStatus.SENT_TO_FINANCE, actor, ip, note="ارسال به مالی")
    db.session.commit()
    return _load(req.id)


def set_review_status(actor: User, request_id: int, status: str, note: str | None, ip: str | None = None) -> PurchaseRequest:
    """The expert's decision on the request (cartable): pending / approved / rejected / needs revision.
    Works on any request (a paper request may be recorded first and judged later); a rejected request stays in the records."""
    require(actor, "update")
    req = _load(request_id)
    new = ReviewStatus(status)
    if new in (ReviewStatus.REJECTED, ReviewStatus.NEEDS_REVISION):
        _need(note, "علت رد یا موارد اصلاحی را بنویسید.", "note")
    old = req.review_status
    req.review_status = new
    req.review_note = note if new != ReviewStatus.PENDING_REVIEW or note else None
    req.reviewed_at = _now()
    req.reviewed_by_name = (actor.full_name or "")[:200] or None
    if old != new:
        _event(req, actor, "REVIEW", from_status=old, to_status=new, note=note)
        _audit(actor, req, "review_status_change", {"from": old.value, "to": new.value, "note": note}, ip)
    db.session.commit()
    return _load(req.id)


def cancel(actor: User, request_id: int, note: str | None, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    _need(note, "علت لغو را بنویسید.", "note")
    req.status_note = note
    _set_status(req, PurchaseStatus.CANCELLED, actor, ip, note=note)
    db.session.commit()
    return _load(req.id)


def send_back(actor: User, request_id: int, note: str | None, ip: str | None = None) -> PurchaseRequest:
    """Ask for corrections (also reopens a completed / cancelled request). Needs `approve`."""
    require(actor, "approve")
    req = _load(request_id)
    _need(req.status != PurchaseStatus.DRAFT, "پیش‌نویس نیازی به اصلاح ندارد.", "note")
    _need(note, "توضیح موارد اصلاحی را بنویسید.", "note")
    req.status_note = note
    if req.status == PurchaseStatus.COMPLETED:
        req.completed_at = None
    _set_status(req, PurchaseStatus.NEEDS_REVISION, actor, ip, note=note)
    db.session.commit()
    return _load(req.id)


def resubmit(actor: User, request_id: int, ip: str | None = None) -> PurchaseRequest:
    req = _editable(actor, request_id)
    _need(req.status == PurchaseStatus.NEEDS_REVISION, "این درخواست در وضعیت اصلاح نیست.", "status")
    return submit(actor, request_id, ip)


def delete_request(actor: User, request_id: int, ip: str | None = None) -> None:
    require(actor, "delete")
    req = _load(request_id)
    if req.status not in (PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED):
        raise ConflictError("فقط پیش‌نویس یا درخواست لغوشده حذف می‌شود؛ ابتدا درخواست را لغو کنید.")
    req.deleted_at = _now()
    _audit(actor, req, "delete", {"status": req.status.value}, ip)
    db.session.commit()


def upload_file(actor: User, file) -> PurchaseFile:
    if not (can(actor, "create") or can(actor, "update")):
        require(actor, "create")
    from app.modules.purchases import files
    return files.save_upload(file, uploaded_by_user_id=actor.id)
