"""
Lists, KPI dashboard, commodity-group analysis and export tables for /api/purchases.

ONE filter object drives everything (list, KPIs, charts, groups, exports), so the numbers on a screen,
in its table and in a downloaded file always agree. Nothing here is estimated or invented: every figure
is read from the recorded requests; where a figure cannot be known (no approved reference price, no
price for a planned purchase) the response says how many records were left out instead of guessing.

Definitions (also returned by the dashboard as `definitions`):
  * the date filter works on the request's registration date (تاریخ ثبت) for every figure;
  * a request counts once registered (drafts are not counted); cancelled ones stay in the total;
  * open = every non-draft status that is neither completed nor cancelled;
  * spent = final amount of COMPLETED purchases (items x final unit price, plus extra costs unless the
    filter narrows to some items -- extra costs belong to the whole request, not to one item);
  * savings = sum over COMPLETED purchases of (approved reference unit price - final unit price) x
    purchased quantity, only for items that have an approved reference price (negative stays negative).
"""
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.modules.purchases import labels as L
from app.modules.purchases import services as S
from app.modules.purchases.models import (
    OPEN_STATUSES, PurchaseDirect, PurchaseInquiry, PurchaseInquiryItem, PurchaseItem, PurchaseRequest, PurchaseStatus,
    ReviewStatus,
)
from app.modules.suppliers.models import SupplierCategory
from app.utils.exceptions import InvalidInputError
from app.utils.jalali import format_jalali, jalali_month_range, parse_date_input, tehran_today, to_jalali

ZERO = Decimal("0")


# ── filters ──────────────────────────────────────────────────────────
@dataclass
class Filters:
    date_from: date | None = None
    date_to: date | None = None
    category_id: int | None = None
    statuses: list[PurchaseStatus] = field(default_factory=list)
    review_statuses: list[ReviewStatus] = field(default_factory=list)
    supplier_id: int | None = None
    supplier_q: str | None = None
    unit: str | None = None
    request_no: str | None = None
    item_q: str | None = None
    granularity: str = "month"

    @property
    def requests_only(self) -> bool:
        """filters that only exist on requests: with one of them set, direct purchases are left out"""
        return bool(self.statuses or self.review_statuses or self.unit or self.request_no)

    @property
    def item_level(self) -> bool:
        """True when the filter narrows to some ITEMS of a request (group / item name)."""
        return self.category_id is not None or bool(self.item_q)


def _parse_date(value, field_name: str, label: str):
    if not value:
        return None
    try:
        return parse_date_input(value)
    except (ValueError, TypeError):
        raise InvalidInputError(f"«{label}» معتبر نیست.", field_name) from None


def parse_filters(args) -> Filters:
    f = Filters()
    f.date_from = _parse_date(args.get("date_from"), "date_from", "از تاریخ")
    f.date_to = _parse_date(args.get("date_to"), "date_to", "تا تاریخ")
    if f.date_from and f.date_to and f.date_from > f.date_to:
        raise InvalidInputError("بازهٔ زمانی معتبر نیست: «از تاریخ» بعد از «تا تاریخ» است.", "date_from")
    for name in ("category_id", "supplier_id"):
        raw = args.get(name)
        if raw not in (None, ""):
            try:
                setattr(f, name, int(raw))
            except ValueError:
                raise InvalidInputError("مقدار فیلتر معتبر نیست.", name) from None
    for raw in (args.get("status") or "").split(","):
        raw = raw.strip()
        if raw:
            try:
                f.statuses.append(PurchaseStatus(raw))
            except ValueError:
                raise InvalidInputError("وضعیت معتبر نیست.", "status") from None
    for raw in (args.get("review_status") or "").split(","):
        raw = raw.strip()
        if raw:
            try:
                f.review_statuses.append(ReviewStatus(raw))
            except ValueError:
                raise InvalidInputError("وضعیت بررسی معتبر نیست.", "review_status") from None
    f.supplier_q = (args.get("supplier") or "").strip()[:100] or None
    f.unit = (args.get("unit") or "").strip()[:200] or None
    f.request_no = (args.get("request_no") or "").strip()[:30] or None
    f.item_q = (args.get("item") or "").strip()[:100] or None
    g = (args.get("granularity") or "month").strip()
    f.granularity = g if g in ("day", "week", "month") else "month"
    return f


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"


def conditions(f: Filters, *, with_dates: bool = True, with_statuses: bool = True, exclude_drafts: bool = False) -> list:
    R = PurchaseRequest
    c = [R.deleted_at.is_(None), R.flow_version == 1]   # item-based requests (flow.py) have their own KPIs
    if exclude_drafts:
        c.append(R.status != PurchaseStatus.DRAFT)
    if with_dates and f.date_from:
        c.append(R.request_date >= f.date_from)
    if with_dates and f.date_to:
        c.append(R.request_date <= f.date_to)
    if with_statuses and f.statuses:
        c.append(R.status.in_(f.statuses))
    if with_statuses and f.review_statuses:
        c.append(R.review_status.in_(f.review_statuses))
    if f.unit:
        c.append(R.requester_unit == f.unit)
    if f.request_no:
        c.append(R.request_no.like(_like(f.request_no), escape="\\"))
    if f.category_id is not None:
        c.append(exists().where(PurchaseItem.request_id == R.id, PurchaseItem.category_id == f.category_id))
    if f.item_q:
        c.append(exists().where(PurchaseItem.request_id == R.id, PurchaseItem.name.like(_like(f.item_q), escape="\\")))
    if f.supplier_id is not None:
        c.append(exists().where(PurchaseInquiry.request_id == R.id, PurchaseInquiry.supplier_id == f.supplier_id))
    if f.supplier_q:
        c.append(exists().where(PurchaseInquiry.request_id == R.id,
                                PurchaseInquiry.supplier_name.like(_like(f.supplier_q), escape="\\")))
    return c


def item_conditions(f: Filters) -> list:
    c = []
    if f.category_id is not None:
        c.append(PurchaseItem.category_id == f.category_id)
    if f.item_q:
        c.append(PurchaseItem.name.like(_like(f.item_q), escape="\\"))
    return c


# ── list ─────────────────────────────────────────────────────────────
SORTS = {
    "request_no": PurchaseRequest.request_no, "request_date": PurchaseRequest.request_date,
    "subject": PurchaseRequest.subject, "requester_unit": PurchaseRequest.requester_unit,
    "status": PurchaseRequest.status, "priority": PurchaseRequest.priority,
    "budget_amount": PurchaseRequest.budget_amount, "final_amount": PurchaseRequest.final_amount,
    "required_date": PurchaseRequest.required_date, "created_at": PurchaseRequest.created_at,
}
KPI_KEYS = ("total", "completed", "open", "spent", "savings", "next_month")


def next_month_range(today: date | None = None) -> tuple[date, date, str]:
    jy, jm, _ = to_jalali(today or tehran_today())
    jy, jm = (jy + 1, 1) if jm == 12 else (jy, jm + 1)
    start, end = jalali_month_range(jy, jm)
    return start, end, f"{jy:04d}/{jm:02d}"


def _savings_expr():
    I = PurchaseItem
    ok = and_(I.reference_unit_price.is_not(None), I.reference_approved_at.is_not(None),
              I.final_unit_price.is_not(None), I.purchased_quantity.is_not(None))
    return case((ok, (I.reference_unit_price - I.final_unit_price) * I.purchased_quantity), else_=None)


def _kpi_conditions(kpi: str | None, f: Filters) -> list:
    R = PurchaseRequest
    if kpi is None:
        return conditions(f)
    if kpi not in KPI_KEYS:
        raise InvalidInputError("شاخص نامعتبر است.", "kpi")
    c = conditions(f, with_dates=(kpi != "next_month"), exclude_drafts=True)
    if kpi in ("completed", "spent", "savings"):
        c.append(R.status == PurchaseStatus.COMPLETED)
    elif kpi in ("open", "next_month"):
        c.append(R.status.in_(OPEN_STATUSES))
        c.append(R.review_status != ReviewStatus.REJECTED)
    if kpi == "next_month":
        start, end, _ = next_month_range()
        c += [R.required_date >= start, R.required_date <= end]
    if kpi == "savings":
        c.append(exists().where(PurchaseItem.request_id == R.id, _savings_expr().is_not(None)))
    return c


def list_requests(actor, f: Filters, *, page: int, per_page: int, sort: str = "created_at",
                  direction: str = "desc", kpi: str | None = None):
    S.require(actor, "read")
    R = PurchaseRequest
    conds = _kpi_conditions(kpi, f)
    total = db.session.scalar(select(func.count()).select_from(R).where(*conds)) or 0
    col = SORTS.get(sort, R.created_at)
    order = col.asc() if direction == "asc" else col.desc()
    rows = db.session.scalars(
        select(R).where(*conds).order_by(order, R.id.desc()).offset((page - 1) * per_page).limit(per_page)
        .options(selectinload(R.selected_inquiry))
    ).all()
    ids = [r.id for r in rows]
    items = defaultdict(list)
    if ids:
        for it in db.session.scalars(select(PurchaseItem).where(PurchaseItem.request_id.in_(ids)).order_by(PurchaseItem.position)):
            items[it.request_id].append(it)
    out = []
    for r in rows:
        its = items.get(r.id, [])
        est = (sum((S._dec(i.quantity) * S._dec(i.estimated_unit_price) for i in its), ZERO)
               if its and all(i.estimated_unit_price is not None for i in its) else None)
        sav = [S.item_savings(i) for i in its] if r.status == PurchaseStatus.COMPLETED else []
        sav = [s for s in sav if s is not None]
        row = {
            "id": r.id, "request_no": r.request_no, "status": r.status.value, "status_label": L.STATUS[r.status.value],
            "priority": r.priority.value, "priority_label": L.PRIORITY[r.priority.value],
            "review_status": r.review_status.value, "review_label": L.REVIEW[r.review_status.value], "review_note": r.review_note,
            "requester_unit": r.requester_unit, "requester_name": r.requester_name, "subject": r.subject,
            "request_date": r.request_date.isoformat() if r.request_date else None,
            "request_date_jalali": format_jalali(r.request_date),
            "required_date_jalali": format_jalali(r.required_date),
            "budget_amount": S.num(r.budget_amount), "estimated_total": S.num(est), "final_amount": S.num(r.final_amount),
            "savings": S.num(sum(sav, ZERO)) if sav else None,
            "supplier_name": r.selected_inquiry.supplier_name if r.selected_inquiry else None,
            "categories": sorted({i.category_name for i in its}), "items_count": len(its),
            "current_step": r.current_step, "creator_name": r.creator_name,
        }
        if kpi == "next_month":
            amount, basis = _forecast_amount(r, its, f)
            row["forecast_amount"], row["forecast_basis"] = S.num(amount), basis
        out.append(row)
    return out, total


# ── forecast for the next month ──────────────────────────────────────
def _forecast_amount(req: PurchaseRequest, items: list, f: Filters):
    """Amount planned for an open request, best information first:
    selected quotation (agreed prices) -> estimated prices of the items -> the budget entered on the request.
    When the filter narrows to some items only item-based amounts are used (a budget belongs to the whole request).
    Returns (amount | None, basis)."""
    if f.item_level:
        items = [i for i in items if (f.category_id is None or i.category_id == f.category_id)
                 and (not f.item_q or f.item_q.lower() in (i.name or "").lower())]
    if req.selected_inquiry_id is not None and items and all(i.final_unit_price is not None for i in items):
        total = sum((S._dec(i.final_unit_price) * S._dec(i.quantity) for i in items), ZERO)
        if not f.item_level and req.selected_inquiry is not None:
            total += S._dec(req.selected_inquiry.extra_costs) or ZERO
        return total, "selected_quote"
    if items and all(i.estimated_unit_price is not None for i in items):
        return sum((S._dec(i.estimated_unit_price) * S._dec(i.quantity) for i in items), ZERO), "estimate"
    if not f.item_level and req.budget_amount is not None:
        return S._dec(req.budget_amount), "budget"
    return None, None


def next_month_forecast(f: Filters) -> dict:
    start, end, label = next_month_range()
    R = PurchaseRequest
    conds = conditions(f, with_dates=False, exclude_drafts=True)
    conds += [R.status.in_(OPEN_STATUSES), R.review_status != ReviewStatus.REJECTED,
              R.required_date >= start, R.required_date <= end]
    reqs = db.session.scalars(select(R).where(*conds).options(selectinload(R.items), selectinload(R.selected_inquiry))).all()
    total, unpriced = ZERO, 0
    basis = {k: {"count": 0, "amount": ZERO} for k in ("selected_quote", "estimate", "budget")}
    for r in reqs:
        amount, b = _forecast_amount(r, r.items, f)
        if amount is None:
            unpriced += 1
            continue
        basis[b]["count"] += 1
        basis[b]["amount"] += amount
        total += amount
    return {
        "month": label, "from": start.isoformat(), "to": end.isoformat(),
        "from_jalali": format_jalali(start), "to_jalali": format_jalali(end),
        "amount": S.num(total), "requests_count": len(reqs), "unpriced_count": unpriced,
        "basis": {k: {"count": v["count"], "amount": S.num(v["amount"])} for k, v in basis.items()},
    }


# ── buckets for the trend charts ─────────────────────────────────────
def _bucket_key(d: date, gran: str):
    if gran == "month":
        jy, jm, _ = to_jalali(d)
        return (jy, jm)
    if gran == "week":
        return d - timedelta(days=(d.weekday() + 2) % 7)  # Jalali weeks start on Saturday
    return d


def _bucket_label(key, gran: str) -> str:
    if gran == "month":
        return f"{key[0]:04d}/{key[1]:02d}"
    return format_jalali(key)


def _bucket_range(d1: date, d2: date, gran: str) -> list:
    keys, seen, cur = [], set(), d1
    while cur <= d2 and len(keys) < 800:
        k = _bucket_key(cur, gran)
        if k not in seen:
            seen.add(k)
            keys.append(k)
        cur += timedelta(days=1)
    return keys


# ── dashboard ────────────────────────────────────────────────────────
DEFINITIONS = {
    "total": "همهٔ درخواست‌های ثبت‌شده (به‌جز پیش‌نویس‌ها)، شامل لغوشده‌ها؛ بر اساس تاریخ ثبت.",
    "completed": "درخواست‌های پایان‌یافته: خرید انجام و کالا کامل تحویل شده است.",
    "open": "درخواست‌های باز و در جریان بررسی: نه پایان‌یافته‌اند، نه لغو و نه ردشده؛ در هر مرحلهٔ گردش کار.",
    "spent": "مجموع هزینه به ریال: خریدهای پایان‌یافتهٔ درخواست‌ها (اقلام × قیمت نهایی + هزینه‌های جانبی؛ با فیلتر گروه/کالا فقط اقلام) به‌علاوهٔ خریدهای مستقیم.",
    "direct": "خریدهای مستقیم ثبت‌شده بدون درخواست و استعلام (بر اساس تاریخ خرید). با فیلتر وضعیت، وضعیت بررسی، واحد متقاضی یا شماره درخواست، در محاسبه نمی‌آیند.",
    "savings": "مجموع (قیمت مبنای تأییدشده − قیمت نهایی) × مقدار خریداری‌شده به ریال، فقط برای اقلامی که قیمت مبنای تأییدشده دارند.",
    "next_month": "اقلام درخواست‌های بازِ موردنیاز در ماه شمسی بعد: قیمت توافقی ← برآورد اقلام ← بودجهٔ درخواست.",
}


def direct_conditions(f: Filters) -> list:
    D = PurchaseDirect
    c = [D.deleted_at.is_(None)]
    if f.date_from:
        c.append(D.purchase_date >= f.date_from)
    if f.date_to:
        c.append(D.purchase_date <= f.date_to)
    if f.category_id is not None:
        c.append(D.category_id == f.category_id)
    if f.supplier_id is not None:
        c.append(D.supplier_id == f.supplier_id)
    if f.supplier_q:
        c.append(D.supplier_name.like(_like(f.supplier_q), escape="\\"))
    if f.item_q:
        c.append(D.title.like(_like(f.item_q), escape="\\"))
    return c


def direct_rows(f: Filters) -> list:
    """Direct purchases that match the filters (none when a request-only filter is set)."""
    if f.requests_only:
        return []
    D = PurchaseDirect
    return db.session.execute(
        select(D.id, D.purchase_date, D.category_id, D.category_name, D.supplier_id, D.supplier_name, D.amount).where(*direct_conditions(f))
    ).all()


def review_counts(f: Filters) -> list[dict]:
    """Requests per review status under every filter EXCEPT the review filter itself (drafts included: this is the cartable)."""
    R = PurchaseRequest
    rows = dict(db.session.execute(
        select(R.review_status, func.count()).where(*conditions(replace(f, review_statuses=[]))).group_by(R.review_status)).all())
    return [{"status": k, "label": v, "count": int(rows.get(ReviewStatus(k), 0))} for k, v in L.REVIEW.items()]


def dashboard(actor, f: Filters) -> dict:
    S.require(actor, "read")
    R, I = PurchaseRequest, PurchaseItem
    conds = conditions(f, exclude_drafts=True)
    req_rows = db.session.execute(
        select(R.id, R.request_date, R.status, R.review_status, R.final_extra_costs, R.selected_inquiry_id).where(*conds)
    ).all()
    ids_sub = select(R.id).where(*conds)
    item_rows = db.session.execute(
        select(I.request_id, I.category_id, I.category_name, I.quantity, I.estimated_unit_price,
               I.final_unit_price, I.purchased_quantity, _savings_expr().label("sav"),
               I.reference_unit_price.is_not(None).label("has_ref"))
        .where(I.request_id.in_(ids_sub), *item_conditions(f))
    ).all()
    status_of = {r.id: r.status for r in req_rows}
    review_of = {r.id: r.review_status for r in req_rows}
    directs = direct_rows(f)
    date_of = {r.id: r.request_date for r in req_rows}
    extra_of = {r.id: S._dec(r.final_extra_costs) or ZERO for r in req_rows}

    per_req = defaultdict(lambda: {"est": ZERO, "fin": ZERO, "sav": ZERO, "sav_n": 0, "items": 0,
                                   "cmp_est": ZERO, "cmp_fin": ZERO})
    per_cat = defaultdict(lambda: {"all": set(), "done": set(), "open": set(), "spent": ZERO, "sav": ZERO,
                                   "sav_n": 0, "items": 0, "name": "", "dcount": 0, "damount": ZERO})
    for it in item_rows:
        st = status_of.get(it.request_id)
        if st is None:
            continue
        cat = per_cat[it.category_id if it.category_id is not None else f"x:{it.category_name}"]
        cat["name"] = cat["name"] or it.category_name
        cat["all"].add(it.request_id)
        if st == PurchaseStatus.COMPLETED:
            cat["done"].add(it.request_id)
        elif st in OPEN_STATUSES:
            cat["open"].add(it.request_id)
        pr = per_req[it.request_id]
        pr["items"] += 1
        if st == PurchaseStatus.COMPLETED:
            fin = S._dec(it.final_unit_price) * S._dec(it.purchased_quantity) if it.final_unit_price is not None and it.purchased_quantity is not None else ZERO
            pr["fin"] += fin
            cat["spent"] += fin
            cat["items"] += 1
            if it.estimated_unit_price is not None and it.final_unit_price is not None and it.purchased_quantity is not None:
                pr["cmp_est"] += S._dec(it.estimated_unit_price) * S._dec(it.purchased_quantity)
                pr["cmp_fin"] += fin
            if it.sav is not None:
                pr["sav"] += S._dec(it.sav)
                pr["sav_n"] += 1
                cat["sav"] += S._dec(it.sav)
                cat["sav_n"] += 1

    for d in directs:  # direct purchases join the group analysis through their commodity group
        key = d.category_id if d.category_id is not None else f"x:{d.category_name or 'بدون گروه کالایی'}"
        cat = per_cat[key]
        cat["name"] = cat["name"] or d.category_name or "بدون گروه کالایی"
        cat["dcount"] += 1
        cat["damount"] += S._dec(d.amount)
    direct_total = sum((S._dec(d.amount) for d in directs), ZERO)

    status_counts = defaultdict(int)
    for st in status_of.values():
        status_counts[st.value] += 1
    completed_ids = [i for i, s in status_of.items() if s == PurchaseStatus.COMPLETED]
    spent = ZERO
    for i in completed_ids:
        spent += per_req[i]["fin"] + (ZERO if f.item_level else extra_of[i])
    savings = sum((per_req[i]["sav"] for i in completed_ids), ZERO)
    sav_items = sum(per_req[i]["sav_n"] for i in completed_ids)
    done_items = sum(per_req[i]["items"] for i in completed_ids)

    kpis = {
        "total": {"value": len(status_of), "cancelled": status_counts.get("CANCELLED", 0)},
        "completed": {"value": len(completed_ids)},
        "open": {"value": sum(1 for i, st in status_of.items() if st in OPEN_STATUSES and review_of[i] != ReviewStatus.REJECTED)},
        "spent": {"value": S.num(spent + direct_total), "requests_amount": S.num(spent), "direct_amount": S.num(direct_total),
                  "extra_costs_included": not f.item_level},
        "direct": {"value": len(directs), "amount": S.num(direct_total)},
        "savings": {"value": S.num(savings) if sav_items else None, "items_counted": sav_items,
                    "items_total": done_items, "items_without_reference": done_items - sav_items},
        "next_month": next_month_forecast(f),
    }

    # trends -------------------------------------------------------------
    dates = [d for d in date_of.values() if d] + [d.purchase_date for d in directs]
    d1 = f.date_from or (min(dates) if dates else None)
    d2 = f.date_to or (max(dates) if dates else None)
    gran = f.granularity
    keys = _bucket_range(d1, d2, gran) if d1 and d2 else []
    if len(keys) >= 800 and gran != "month":
        gran = "month"
        keys = _bucket_range(d1, d2, gran)
    tr = {k: {"count": 0, "spent": ZERO, "est": ZERO, "fin": ZERO, "sav": ZERO, "sav_n": 0, "direct": ZERO} for k in keys}
    for d in directs:
        b = tr.get(_bucket_key(d.purchase_date, gran))
        if b is not None:
            b["direct"] += S._dec(d.amount)
    for rid, d in date_of.items():
        if d is None:
            continue
        b = tr.get(_bucket_key(d, gran))
        if b is None:
            continue
        b["count"] += 1
        if status_of[rid] == PurchaseStatus.COMPLETED:
            pr = per_req[rid]
            b["spent"] += pr["fin"] + (ZERO if f.item_level else extra_of[rid])
            b["est"] += pr["cmp_est"]
            b["fin"] += pr["cmp_fin"]
            b["sav"] += pr["sav"]
            b["sav_n"] += pr["sav_n"]
    trend = [{"label": _bucket_label(k, gran), "requests": v["count"], "spent": S.num(v["spent"]),
              "estimated": S.num(v["est"]), "final": S.num(v["fin"]), "direct_spent": S.num(v["direct"]),
              "savings": S.num(v["sav"]) if v["sav_n"] else None} for k, v in tr.items()]

    # commodity groups ------------------------------------------------------
    active = S.main_categories()
    groups, seen = [], set()
    for c in active:
        if f.category_id is not None and c.id != f.category_id:
            continue
        groups.append(_group_row(c.id, c.name, per_cat.get(c.id)))
        seen.add(c.id)
    for key, v in per_cat.items():
        if key not in seen:  # a group that was renamed away / deactivated still shows its history
            groups.append(_group_row(key if isinstance(key, int) else None, v["name"], v, inactive=isinstance(key, int)))

    suppliers = _supplier_performance(f, conds, directs)
    return {
        "filters_applied": {"date_from": f.date_from.isoformat() if f.date_from else None,
                            "date_to": f.date_to.isoformat() if f.date_to else None, "granularity": gran},
        "definitions": DEFINITIONS, "kpis": kpis,
        "status_counts": [{"status": s, "label": L.STATUS[s], "count": n} for s, n in status_counts.items()],
        "review_counts": review_counts(f),
        "groups": groups, "trend": trend, "suppliers": suppliers,
    }


def _group_row(cid, name, v, inactive: bool = False) -> dict:
    v = v or {"all": set(), "done": set(), "open": set(), "spent": ZERO, "sav": ZERO, "sav_n": 0, "dcount": 0, "damount": ZERO}
    return {
        "category_id": cid, "name": name, "inactive": inactive,
        "requests": len(v["all"]), "completed": len(v["done"]), "open": len(v["open"]),
        "spent": S.num(v["spent"] + v["damount"]), "requests_spent": S.num(v["spent"]),
        "direct_count": v["dcount"], "direct_spent": S.num(v["damount"]),
        "savings": S.num(v["sav"]) if v["sav_n"] else None, "savings_items": v["sav_n"],
    }


def _supplier_performance(f: Filters, conds: list, directs: list) -> list[dict]:
    """Per supplier: how often it was quoted / selected, the amount awarded, how often it was the cheapest."""
    R, Q = PurchaseRequest, PurchaseInquiry
    ids_sub = select(R.id).where(*conds)
    n_items = dict(db.session.execute(
        select(PurchaseItem.request_id, func.count()).where(PurchaseItem.request_id.in_(ids_sub)).group_by(PurchaseItem.request_id)).all())
    n_lines = dict(db.session.execute(
        select(PurchaseInquiryItem.inquiry_id, func.count()).join(Q, Q.id == PurchaseInquiryItem.inquiry_id)
        .where(Q.request_id.in_(ids_sub)).group_by(PurchaseInquiryItem.inquiry_id)).all())
    inqs = db.session.execute(
        select(Q.id, Q.request_id, Q.supplier_id, Q.supplier_name, Q.total_price, Q.delivery_days)
        .where(Q.request_id.in_(ids_sub))).all()
    sel = {r.id: r.selected_inquiry_id for r in db.session.execute(select(R.id, R.selected_inquiry_id, R.status, R.final_amount).where(*conds)).all()}
    done = {r.id: (r.final_amount) for r in db.session.execute(
        select(R.id, R.final_amount).where(*conds, R.status == PurchaseStatus.COMPLETED))}
    by_req = defaultdict(list)
    for q in inqs:
        if n_lines.get(q.id, 0) == n_items.get(q.request_id, -1):
            by_req[q.request_id].append(q)
    stats = {}
    for q in inqs:
        key = q.supplier_id if q.supplier_id is not None else f"x:{q.supplier_name}"
        s = stats.setdefault(key, {"supplier_id": q.supplier_id, "name": q.supplier_name, "inquiries": 0, "selected": 0,
                                   "cheapest": 0, "compared": 0, "awarded": ZERO, "delivery_days": [],
                                   "direct_count": 0, "direct_amount": ZERO})
        s["inquiries"] += 1
        if q.delivery_days is not None:
            s["delivery_days"].append(q.delivery_days)
        if sel.get(q.request_id) == q.id:
            s["selected"] += 1
            if q.request_id in done:
                s["awarded"] += S._dec(done[q.request_id]) or ZERO
    for rid, qs in by_req.items():
        if len(qs) < 2:
            continue
        low = min(S._dec(q.total_price) for q in qs)
        for q in qs:
            key = q.supplier_id if q.supplier_id is not None else f"x:{q.supplier_name}"
            stats[key]["compared"] += 1
            if S._dec(q.total_price) == low:
                stats[key]["cheapest"] += 1
    for d in directs:  # direct purchases count towards the supplier's purchases
        key = d.supplier_id if d.supplier_id is not None else f"x:{d.supplier_name}"
        st = stats.setdefault(key, {"supplier_id": d.supplier_id, "name": d.supplier_name, "inquiries": 0, "selected": 0,
                                    "cheapest": 0, "compared": 0, "awarded": ZERO, "delivery_days": [],
                                    "direct_count": 0, "direct_amount": ZERO})
        st["direct_count"] += 1
        st["direct_amount"] += S._dec(d.amount)
    out = []
    for s in stats.values():
        days = s.pop("delivery_days")
        out.append({**s, "awarded": S.num(s["awarded"]), "direct_amount": S.num(s["direct_amount"]),
                    "win_rate": round(s["selected"] * 100 / s["inquiries"], 1) if s["inquiries"] else None,
                    "cheapest_rate": round(s["cheapest"] * 100 / s["compared"], 1) if s["compared"] else None,
                    "avg_delivery_days": round(sum(days) / len(days), 1) if days else None})
    out.sort(key=lambda r: (-(r["selected"]), -(r["inquiries"]), r["name"] or ""))
    return out


# ── export tables ────────────────────────────────────────────────────
EXPORT_KINDS = {
    "overview": "گزارش کلی عملکرد خرید", "groups": "گزارش تفکیکی گروه‌های کالایی", "requests": "ریز اطلاعات درخواست‌ها",
    "inquiries": "گزارش مقایسه استعلام‌ها", "suppliers": "گزارش تأمین‌کنندگان منتخب", "costs": "گزارش هزینه‌ها و صرفه‌جویی",
    "direct": "گزارش خریدهای مستقیم",
}


def _jd(d):
    return format_jalali(d) if d else ""


def export_table(actor, kind: str, f: Filters) -> tuple[str, list[str], list[list]]:
    """(title, headers, rows) for one report, always built from the SAME filters as the screen."""
    S.require(actor, "read")
    S.require(actor, "export")
    if kind not in EXPORT_KINDS:
        raise InvalidInputError("نوع گزارش نامعتبر است.", "kind")
    title = EXPORT_KINDS[kind]
    R = PurchaseRequest
    if kind in ("overview", "groups", "suppliers"):
        dash = dashboard(actor, f)
        if kind == "overview":
            k = dash["kpis"]
            nm = k["next_month"]
            rows = [
                ["تعداد کل درخواست‌های خرید", k["total"]["value"]], ["تعداد خریدهای پایان‌یافته", k["completed"]["value"]],
                ["درخواست‌های باز و در جریان بررسی", k["open"]["value"]], ["مجموع هزینه‌های انجام‌شده، شامل خرید مستقیم (ریال)", k["spent"]["value"]],
                ["تعداد خریدهای مستقیم", k["direct"]["value"]], ["مبلغ خریدهای مستقیم (ریال)", k["direct"]["amount"]],
                ["میزان صرفه‌جویی محقق‌شده (ریال)", k["savings"]["value"] if k["savings"]["value"] is not None else "بدون قیمت مبنای تأییدشده"],
                [f"بودجه پیش‌بینی‌شده ماه آینده ({nm['month']}) (ریال)", nm["amount"]],
            ] + [[f"وضعیت بررسی: {s['label']}", s["count"]] for s in dash["review_counts"]] \
              + [[f"وضعیت گردش کار: {s['label']}", s["count"]] for s in dash["status_counts"]]
            return title, ["شاخص", "مقدار"], rows
        if kind == "groups":
            return title, ["گروه کالایی", "کل درخواست‌ها", "پایان‌یافته", "باز", "خریدهای مستقیم (تعداد)", "خریدهای مستقیم (ریال)",
                       "مجموع هزینه (ریال)", "صرفه‌جویی (ریال)"], [
                [g["name"], g["requests"], g["completed"], g["open"], g["direct_count"], g["direct_spent"], g["spent"],
                 g["savings"] if g["savings"] is not None else ""] for g in dash["groups"]]
        return title, ["تأمین‌کننده", "تعداد استعلام", "تعداد انتخاب‌شده", "درصد انتخاب", "دفعات کمترین قیمت",
                       "مبلغ خریدهای پایان‌یافته (ریال)", "خریدهای مستقیم (تعداد)", "خریدهای مستقیم (ریال)", "میانگین زمان تحویل (روز)"], [
            [s["name"], s["inquiries"], s["selected"], s["win_rate"] if s["win_rate"] is not None else "",
             s["cheapest"], s["awarded"], s["direct_count"], s["direct_amount"], s["avg_delivery_days"] if s["avg_delivery_days"] is not None else ""]
            for s in dash["suppliers"]]
    conds = conditions(f, exclude_drafts=False)
    limit = 10_000
    if kind == "requests":
        reqs = db.session.scalars(select(R).where(*conds).order_by(R.request_date.desc(), R.id.desc()).limit(limit)
                                  .options(selectinload(R.items), selectinload(R.selected_inquiry))).all()
        rows = []
        for r in reqs:
            est = S.estimated_total(r)
            sav = [S.item_savings(i) for i in r.items] if r.status == PurchaseStatus.COMPLETED else []
            sav = [s for s in sav if s is not None]
            rows.append([r.request_no, L.STATUS[r.status.value], L.REVIEW[r.review_status.value], r.review_note or "",
                         L.PRIORITY[r.priority.value], r.requester_unit or "",
                         r.requester_name or "", r.subject or "", _jd(r.request_date), _jd(r.required_date),
                         "، ".join(sorted({i.category_name for i in r.items})), len(r.items),
                         S.num(r.budget_amount) if r.budget_amount is not None else "", S.num(est) if est is not None else "",
                         r.selected_inquiry.supplier_name if r.selected_inquiry else "",
                         S.num(r.final_amount) if r.final_amount is not None else "",
                         S.num(sum(sav, ZERO)) if sav else "", L.DELIVERY[r.delivery_status.value], r.creator_name or ""])
        return title, ["شماره درخواست", "وضعیت گردش کار", "وضعیت بررسی", "توضیح بررسی", "اولویت", "شرکت/واحد متقاضی", "درخواست‌کننده", "موضوع", "تاریخ ثبت",
                       "تاریخ موردنیاز", "گروه‌های کالایی", "تعداد اقلام", "بودجه پیش‌بینی‌شده (ریال)", "برآورد اقلام (ریال)",
                       "تأمین‌کنندهٔ منتخب", "مبلغ نهایی (ریال)", "صرفه‌جویی (ریال)", "وضعیت تحویل", "ثبت‌کننده"], rows
    if kind == "inquiries":
        reqs = db.session.scalars(select(R).where(*conds).order_by(R.request_date.desc(), R.id.desc()).limit(limit)
                                  .options(selectinload(R.items), selectinload(R.inquiries).selectinload(PurchaseInquiry.lines))).all()
        rows = []
        for r in reqs:
            low = S.lowest_inquiry_total(r)
            for q in r.inquiries:
                full = S.inquiry_lines_complete(r, q)
                rows.append([r.request_no, r.subject or "", q.supplier_name, _jd(q.received_date), S.num(q.total_price),
                             S.num(q.extra_costs) if q.extra_costs is not None else "",
                             q.delivery_days if q.delivery_days is not None else "", q.validity_days if q.validity_days is not None else "",
                             q.payment_terms or "", "بله" if full and low is not None and S._dec(q.total_price) == low else "",
                             "بله" if q.id == r.selected_inquiry_id else ""])
        return title, ["شماره درخواست", "موضوع", "تأمین‌کننده", "تاریخ استعلام", "قیمت پیشنهادی کل (ریال)", "هزینه‌های جانبی (ریال)",
                       "زمان تحویل (روز)", "اعتبار (روز)", "شرایط پرداخت", "کمترین قیمت", "انتخاب‌شده"], rows
    if kind == "direct":
        D = PurchaseDirect
        drows = [] if f.requests_only else db.session.scalars(
            select(D).where(*direct_conditions(f)).order_by(D.purchase_date.desc(), D.id.desc()).limit(limit)).all()
        return title, ["شماره خرید / سند", "تاریخ خرید", "شرح و نام کالا یا خدمت", "گروه کالایی", "تأمین‌کننده",
                       "مبلغ خرید (ریال)", "محل مصرف", "توضیحات", "ثبت‌کننده"], [
            [d.doc_no, _jd(d.purchase_date), d.title, d.category_name or "", d.supplier_name, S.num(d.amount),
             d.usage_place, d.description or "", d.creator_name or ""] for d in drows]
    # costs
    items = db.session.execute(
        select(R.request_no, R.status, R.request_date, PurchaseItem)
        .join(PurchaseItem, PurchaseItem.request_id == R.id).where(*conds, *item_conditions(f))
        .order_by(R.request_date.desc(), R.id.desc(), PurchaseItem.position).limit(limit * 3)).all()
    rows = []
    for no, st, rd, it in items:
        sav = S.item_savings(it) if st == PurchaseStatus.COMPLETED else None
        rows.append([no, L.STATUS[st.value], _jd(rd), it.category_name, it.product_code or "", it.name, S.num(it.quantity), it.unit,
                     S.num(it.estimated_unit_price) if it.estimated_unit_price is not None else "",
                     S.num(it.reference_unit_price) if it.reference_unit_price is not None else "",
                     "تأییدشده" if it.reference_approved_at else ("پیشنهادی" if it.reference_unit_price is not None else ""),
                     S.num(it.final_unit_price) if it.final_unit_price is not None else "",
                     S.num(it.purchased_quantity) if it.purchased_quantity is not None else "",
                     S.num(sav) if sav is not None else ""])
    return title, ["شماره درخواست", "وضعیت", "تاریخ ثبت", "گروه کالایی", "کد کالا", "کالا", "تعداد", "واحد", "قیمت تخمینی واحد (ریال)",
                   "قیمت مبنا (ریال)", "وضعیت قیمت مبنا", "قیمت نهایی واحد (ریال)", "مقدار خریداری‌شده", "صرفه‌جویی (ریال)"], rows
