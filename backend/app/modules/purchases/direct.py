"""Direct purchases (خرید مستقیم): a purchase recorded as ONE report line -- no request, no quotations.

Fields: document / purchase number (typed by the expert, unique), purchase date, goods-or-service name (+ optional
description and commodity group), supplier (from the supplier bank, or a free name for a vendor that is not in it),
amount in whole rials and place of use. Same permissions as the rest of the module (read / create / update / delete).
Direct purchases are included in the dashboard and the aggregate reports (reports.py)."""
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.purchases import reports
from app.modules.purchases import services as S
from app.modules.purchases.models import PurchaseDirect
from app.modules.purchases.schemas import DirectIn
from app.modules.suppliers.models import Supplier, SupplierCategory
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.utils.jalali import format_jalali

DOC_RE = re.compile(r"^[\w\-./\\+#()\[\] ]+$", re.UNICODE)
SORTS = {"doc_no": PurchaseDirect.doc_no, "purchase_date": PurchaseDirect.purchase_date, "title": PurchaseDirect.title,
         "supplier_name": PurchaseDirect.supplier_name, "amount": PurchaseDirect.amount,
         "usage_place": PurchaseDirect.usage_place, "created_at": PurchaseDirect.created_at}


def _dict(d: PurchaseDirect) -> dict:
    return {
        "id": d.id, "doc_no": d.doc_no, "purchase_date": d.purchase_date.isoformat(), "purchase_date_jalali": format_jalali(d.purchase_date),
        "title": d.title, "description": d.description, "category_id": d.category_id, "category_name": d.category_name,
        "supplier_id": d.supplier_id, "supplier_name": d.supplier_name, "amount": S.num(d.amount),
        "usage_place": d.usage_place, "creator_name": d.creator_name,
    }


def _check_doc_free(doc_no: str, exclude_id: int | None) -> None:
    q = select(PurchaseDirect.id).where(func.lower(PurchaseDirect.doc_no) == doc_no.lower())  # removed rows count too (unique key)
    if exclude_id is not None:
        q = q.where(PurchaseDirect.id != exclude_id)
    if db.session.scalar(q) is not None:
        raise InvalidInputError("این شمارهٔ خرید / سند قبلاً ثبت شده است.", "doc_no")


def _apply(d: PurchaseDirect, body: DirectIn, *, creating: bool) -> None:
    data = body.model_dump(exclude_unset=not creating)
    if creating or "doc_no" in data:
        doc = " ".join((data.get("doc_no") or "").split())
        S._need(doc, "شمارهٔ خرید یا شمارهٔ سند را وارد کنید.", "doc_no")
        S._need(DOC_RE.match(doc), "شمارهٔ خرید فقط می‌تواند شامل حروف، عدد و - _ . / \\ + # ( ) [ ] باشد.", "doc_no")
        _check_doc_free(doc, d.id)
        d.doc_no = doc
    if creating or "purchase_date" in data:
        d.purchase_date = S._date(data.get("purchase_date"), "purchase_date", label="تاریخ خرید")
        S._need(d.purchase_date, "تاریخ خرید را وارد کنید.", "purchase_date")
    if creating or "title" in data:
        d.title = (data.get("title") or "").strip()
        S._need(d.title, "شرح و نام کالا یا خدمت را وارد کنید.", "title")
    if creating or "usage_place" in data:
        d.usage_place = (data.get("usage_place") or "").strip()
        S._need(d.usage_place, "محل مصرف را وارد کنید.", "usage_place")
    if creating or "amount" in data:
        S._need(data.get("amount") is not None and data["amount"] > 0, "مبلغ خرید را (به ریال) وارد کنید.", "amount")
        d.amount = data["amount"]
    if "description" in data:
        d.description = data["description"]
    if creating or "category_id" in data:
        cid = data.get("category_id")
        if cid is None:
            d.category_id = d.category_name = None
        else:
            cat = db.session.get(SupplierCategory, cid)
            S._need(cat is not None, "گروه کالایی معتبر نیست.", "category_id")
            d.category_id, d.category_name = cat.id, cat.name
    if creating or "supplier_id" in data or "supplier_name" in data:
        sid = data.get("supplier_id")
        if sid is not None:
            sup = db.session.get(Supplier, sid)
            S._need(sup is not None and sup.deleted_at is None, "تأمین‌کنندهٔ انتخاب‌شده در بانک تأمین‌کنندگان پیدا نشد.", "supplier_id")
            d.supplier_id, d.supplier_name = sup.id, sup.display_name
        else:  # a vendor that is not in the supplier bank: its name is typed
            name = (data.get("supplier_name") or "").strip()
            S._need(name, "تأمین‌کننده را انتخاب کنید یا نام او را بنویسید.", "supplier_name")
            d.supplier_id, d.supplier_name = None, name


def list_direct(actor: User, f, *, page: int, per_page: int, sort: str, direction: str) -> tuple[list[dict], int, object]:
    S.require(actor, "read")
    if f.requests_only:
        return [], 0, 0
    conds = reports.direct_conditions(f)
    D = PurchaseDirect
    total = db.session.scalar(select(func.count()).select_from(D).where(*conds)) or 0
    amount = db.session.scalar(select(func.coalesce(func.sum(D.amount), 0)).where(*conds))
    col = SORTS.get(sort, D.created_at)
    rows = db.session.scalars(select(D).where(*conds).order_by(col.asc() if direction == "asc" else col.desc(), D.id.desc())
                              .offset((page - 1) * per_page).limit(per_page)).all()
    return [_dict(r) for r in rows], total, S.num(amount)


def get_direct(actor: User, direct_id: int) -> PurchaseDirect:
    row = db.session.get(PurchaseDirect, direct_id)
    if row is None or row.deleted_at is not None:
        raise NotFoundError("خرید مستقیم پیدا نشد.")
    return row


def create_direct(actor: User, body: DirectIn, ip: str | None = None) -> dict:
    S.require(actor, "create")
    d = PurchaseDirect(created_by_user_id=actor.id, creator_name=(actor.full_name or "")[:200] or None)
    _apply(d, body, creating=True)
    try:
        with db.session.begin_nested():
            db.session.add(d)
            db.session.flush()
    except IntegrityError:
        raise InvalidInputError("این شمارهٔ خرید / سند قبلاً ثبت شده است.", "doc_no") from None
    write_audit_log(user_id=actor.id, action="create", module=S.MODULE, entity_type="purchase_direct", entity_id=d.id,
                    metadata={"doc_no": d.doc_no, "amount": S.num(d.amount), "supplier": d.supplier_name}, ip_address=ip)
    db.session.commit()
    return _dict(d)


def update_direct(actor: User, direct_id: int, body: DirectIn, ip: str | None = None) -> dict:
    S.require(actor, "update")
    d = get_direct(actor, direct_id)
    before = _dict(d)
    _apply(d, body, creating=False)
    after = _dict(d)
    if before != after:
        write_audit_log(user_id=actor.id, action="update", module=S.MODULE, entity_type="purchase_direct", entity_id=d.id,
                        metadata={"before": before, "after": after}, ip_address=ip)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise InvalidInputError("این شمارهٔ خرید / سند قبلاً ثبت شده است.", "doc_no") from None
    return after


def delete_direct(actor: User, direct_id: int, ip: str | None = None) -> None:
    S.require(actor, "delete")
    d = get_direct(actor, direct_id)
    if d.deleted_at is not None:
        raise ConflictError("این مورد قبلاً حذف شده است.")
    d.deleted_at = S._now()
    write_audit_log(user_id=actor.id, action="delete", module=S.MODULE, entity_type="purchase_direct", entity_id=d.id,
                    metadata={"doc_no": d.doc_no, "amount": S.num(d.amount)}, ip_address=ip)
    db.session.commit()
