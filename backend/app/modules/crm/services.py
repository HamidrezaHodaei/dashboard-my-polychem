"""
Service layer for /api/crm (sales, payment methods, analytics).

Permission model -- the SAME RBAC engine as every other module (app/permissions/service.py
`has_permission`), global scope:
    crm.sale.read|create|update|delete      sales, analytics, customer/product pickers (read)
    crm.product.read|create|update|delete   payment-method catalogue (write side)
Checks live here (not in routes.py), like modules/customers/services.py.

Customers AND products are never copied: every query joins `customers` (the customer bank) and
`customer_option_items` (the customer bank's GRADE pick-list, kind=GRADE). Grades are
created / renamed / removed in the customer bank only.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.crm.models import (
    CrmPaymentMethod, CrmSale, DocumentType, SaleStatus, SaleType,
)
from app.modules.crm.schemas import (
    ImportRequest, PaymentMethodIn, PaymentMethodUpdate, SaleCreate, SaleUpdate,
)
from app.modules.customers.models import Customer, CustomerOptionItem, CustomerType, OptionKind
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.utils.jalali import (
    add_jalali_months, format_jalali, jalali_month_range, jalali_year_range, parse_date_input, tehran_today, to_tehran,
    to_jalali,
)

MODULE = "crm"
MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)
PRESETS = ("this_month", "last_1m", "last_3m", "last_6m", "last_12m", "this_year")
_MONEY = Decimal("0.01")
_QTY = Decimal("0.001")


# ---------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------
def _require(actor: User, resource: str, action: str) -> None:
    key = f"crm.{resource}.{action}"
    if not has_permission(actor, key, None, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _require_any_read(actor: User) -> None:
    """Product / payment-method lists feed the sale form AND the catalogue screen."""
    if has_permission(actor, "crm.sale.read", None, None) or has_permission(actor, "crm.product.read", None, None):
        return
    raise PermissionDeniedError("permission_denied", "Missing permission 'crm.sale.read' for this action.")


# ---------------------------------------------------------------------
# Text / customer matching helpers
# ---------------------------------------------------------------------
_AR_TO_FA = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_ZW = re.compile(r"[\u200c\u200f\u200e]")


def normalize_name(value: str | None) -> str:
    """Persian/Arabic letter variants, ZWNJ and spacing collapsed -- so 'شرکت  پلی‌کم' == 'شرکت پلی کم'."""
    text = _ZW.sub(" ", (value or "").translate(_AR_TO_FA))
    return re.sub(r"\s+", " ", text).strip().lower()


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_FA_TO_AR = str.maketrans({"ی": "ي", "ک": "ك"})
_TOKEN_SPLIT = re.compile(r"[\s\u200c\u200f\u200e]+")


def _search_tokens(term: str | None) -> list[str]:
    """Words of a search term. Whitespace AND ZWNJ both split, so 'پلی‌کم', 'پلی کم' and 'پلیکم'
    style spellings all find the same row (each part is matched on its own)."""
    return [t for t in _TOKEN_SPLIT.split((term or "").strip()) if t]


def _token_like_variants(token: str) -> list[str]:
    low = token.lower()
    return [f"%{_escape_like(v)}%" for v in {low, low.translate(_AR_TO_FA), low.translate(_FA_TO_AR)}]


def _tokens_match(term: str | None, columns):
    """AND over the words of `term`; each word must occur in at least one of `columns`
    (Persian/Arabic letter spellings both match). 'علی رضایی' therefore finds first_name='علی' +
    last_name='رضایی', which a whole-string LIKE per column never could."""
    tokens = _search_tokens(term)
    if not tokens:
        return None
    clauses = []
    for tok in tokens:
        ors = []
        for like in _token_like_variants(tok):
            ors += [db.func.lower(db.func.coalesce(col, "")).like(like, escape="\\") for col in columns]
        clauses.append(db.or_(*ors))
    return db.and_(*clauses)


def _customer_text_match(term: str):
    """SQL condition: every word of `term` occurs in the customer's company / brand / first / last
    name -- for an individual customer the brand (نام شرکت یا برند) is searchable exactly like the
    person's own name. Shared by the sale customer picker and Request Sample search."""
    return _tokens_match(term, (Customer.company_name, Customer.brand_name, Customer.first_name, Customer.last_name))


def _customer_names(c: Customer) -> set[str]:
    names = {c.display_name, c.company_name, c.brand_name}
    if c.customer_type == CustomerType.INDIVIDUAL:
        names.add(f"{c.first_name or ''} {c.last_name or ''}")
    return {normalize_name(n) for n in names if n and normalize_name(n)}


def _customer_company(c: Customer) -> str | None:
    """The company / brand shown next to a person's name. Legal customers ARE their company (their
    name already is it), so only individuals carry a separate one."""
    if c.customer_type == CustomerType.LEGAL:
        return None
    return (c.brand_name or c.company_name or "").strip() or None


def customer_label(c: Customer) -> str:
    """'علی رضایی — پلی‌کم' for an individual with a brand, otherwise just the name. Used wherever a
    customer is a bar / slice / headline in a report, so the company is visible next to the person."""
    company = _customer_company(c)
    return f"{c.display_name} — {company}" if company else c.display_name


def _customer_ref(c: Customer) -> dict:
    return {
        "id": c.id, "name": c.display_name, "company": _customer_company(c), "label": customer_label(c),
        "customer_type": c.customer_type.value, "province": c.factory_province, "industry": c.category,
    }


# ---------------------------------------------------------------------
# Filters  (one parser shared by the list, the totals and the charts)
# ---------------------------------------------------------------------
@dataclass
class SaleFilters:
    date_from: date | None = None
    date_to: date | None = None
    jalali_year: int | None = None
    jalali_month: int | None = None
    customer_id: int | None = None
    product_id: int | None = None
    payment_method_id: int | None = None
    sale_type: SaleType | None = None
    document_type: DocumentType | None = None
    status: SaleStatus | None = None
    province: str = ""
    industry: str = ""
    search: str = ""

    def as_dict(self) -> dict:
        """Echoed back with every analytics response so the UI can show exactly what was applied."""
        return {
            "date_from": format_jalali(self.date_from), "date_to": format_jalali(self.date_to),
            "date_from_iso": self.date_from.isoformat() if self.date_from else None,
            "date_to_iso": self.date_to.isoformat() if self.date_to else None,
            "year": self.jalali_year, "month": self.jalali_month, "customer_id": self.customer_id,
            "product_id": self.product_id, "payment_method_id": self.payment_method_id,
            "sale_type": self.sale_type.value if self.sale_type else None,
            "document_type": self.document_type.value if self.document_type else None,
            "status": self.status.value if self.status else None,
            "province": self.province or None, "industry": self.industry or None, "search": self.search or None,
        }


def _int_arg(args, name: str, *, lo: int | None = None, hi: int | None = None) -> int | None:
    raw = (args.get(name) or "").strip()
    if not raw or raw == "all":
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise InvalidInputError(f"'{name}' must be a number.", name) from exc
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise InvalidInputError(f"'{name}' is out of range.", name)
    return value


def _enum_arg(args, name: str, enum_cls):
    raw = (args.get(name) or "").strip().upper()
    if not raw or raw == "ALL":
        return None
    try:
        return enum_cls(raw)
    except ValueError as exc:
        raise InvalidInputError(f"'{name}' is not a valid value.", name) from exc


def _date_arg(args, name: str) -> date | None:
    raw = (args.get(name) or "").strip()
    if not raw:
        return None
    try:
        return parse_date_input(raw)
    except (ValueError, TypeError) as exc:
        raise InvalidInputError(f"'{name}' is not a valid date (use 1405/08/15 or 2026-11-06).", name) from exc


def preset_range(preset: str, today: date | None = None) -> tuple[date, date]:
    """Resolved on the server in JALALI months (not 30-day blocks), anchored to today in Tehran."""
    today = today or tehran_today()
    jy, jm, _ = to_jalali(today)
    if preset == "this_month":
        return jalali_month_range(jy, jm)[0], today
    if preset == "this_year":
        return jalali_year_range(jy)[0], today
    months = {"last_1m": 1, "last_3m": 3, "last_6m": 6, "last_12m": 12}[preset]
    return add_jalali_months(today, -months), today


def parse_filters(args) -> SaleFilters:
    """Query-string -> SaleFilters. Combination rule: everything is AND-ed. An explicit
    date_from/date_to wins over `preset`; year / month narrow further (so
    year=1404&month=9 inside date_from..date_to is the intersection)."""
    f = SaleFilters(
        date_from=_date_arg(args, "date_from"), date_to=_date_arg(args, "date_to"),
        jalali_year=_int_arg(args, "year", lo=1300, hi=1700), jalali_month=_int_arg(args, "month", lo=1, hi=12),
        customer_id=_int_arg(args, "customer_id", lo=1), product_id=_int_arg(args, "product_id", lo=1),
        payment_method_id=_int_arg(args, "payment_method_id", lo=1),
        sale_type=_enum_arg(args, "sale_type", SaleType),
        document_type=_enum_arg(args, "document_type", DocumentType),
        status=_enum_arg(args, "status", SaleStatus),
        province="" if (args.get("province") or "") == "all" else (args.get("province") or "").strip(),
        industry="" if (args.get("industry") or "") == "all" else (args.get("industry") or "").strip(),
        search=(args.get("search") or "").strip(),
    )
    preset = (args.get("preset") or "").strip()
    if preset and preset != "all":
        if preset not in PRESETS:
            raise InvalidInputError("'preset' is not a valid value.", "preset")
        if f.date_from is None and f.date_to is None:
            f.date_from, f.date_to = preset_range(preset)
    if f.date_from and f.date_to and f.date_from > f.date_to:
        raise InvalidInputError("The start date must not be after the end date.", "date_from")
    return f


def _signed(expr):
    """Returns count negatively in every total."""
    return db.case((CrmSale.document_type == DocumentType.RETURN, -expr), else_=expr)


def _apply(query, f: SaleFilters):
    """Adds the WHERE clauses. The query must already select from CrmSale joined to Customer."""
    query = query.filter(CrmSale.deleted_at.is_(None))
    if f.date_from:
        query = query.filter(CrmSale.sale_date >= f.date_from)
    if f.date_to:
        query = query.filter(CrmSale.sale_date <= f.date_to)
    if f.jalali_year:
        query = query.filter(CrmSale.jalali_year == f.jalali_year)
    if f.jalali_month:
        query = query.filter(CrmSale.jalali_month == f.jalali_month)
    if f.customer_id:
        query = query.filter(CrmSale.customer_id == f.customer_id)
    if f.product_id:
        query = query.filter(CrmSale.product_id == f.product_id)
    if f.payment_method_id:
        query = query.filter(CrmSale.payment_method_id == f.payment_method_id)
    if f.sale_type:
        query = query.filter(CrmSale.sale_type == f.sale_type)
    if f.document_type:
        query = query.filter(CrmSale.document_type == f.document_type)
    if f.status:
        query = query.filter(CrmSale.status == f.status)
    if f.province:
        query = query.filter(Customer.factory_province == f.province)
    if f.industry:
        query = query.filter(Customer.category == f.industry)
    if f.search:
        match = _tokens_match(f.search, (
            Customer.company_name, Customer.brand_name, Customer.first_name, Customer.last_name,
            CustomerOptionItem.name, CrmSale.description,
        ))
        if match is not None:
            query = query.filter(match)
    return query


def _base_query(*entities):
    q = db.session.query(*entities) if entities else db.session.query(CrmSale)
    return q.select_from(CrmSale).join(Customer, Customer.id == CrmSale.customer_id).join(
        CustomerOptionItem, CustomerOptionItem.id == CrmSale.product_id
    )


# ---------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------
def _stamp(dt) -> str | None:
    if dt is None:
        return None
    local = to_tehran(dt)
    return f"{format_jalali(local.date())} {local:%H:%M}"


def dump_sale(s: CrmSale) -> dict:
    return {
        "id": s.id,
        "customer": _customer_ref(s.customer),
        "product": {"id": s.product.id, "name": s.product.name},
        "payment_method": {"id": s.payment_method.id, "name": s.payment_method.name} if s.payment_method else None,
        "quantity_kg": float(s.quantity_kg), "unit_price": float(s.unit_price), "amount": float(s.amount),
        "net_amount": float(s.amount) * s.sign, "net_quantity_kg": float(s.quantity_kg) * s.sign,
        "sale_type": s.sale_type.value, "document_type": s.document_type.value, "status": s.status.value,
        "is_return": s.is_return,
        "date": format_jalali(s.sale_date), "date_iso": s.sale_date.isoformat(),
        "jalali_year": s.jalali_year, "jalali_month": s.jalali_month,
        "description": s.description, "created_by_user_id": s.created_by_user_id,
        # who registered the sale (a fixed text, see core/creator_snapshot.py) and exactly when
        "created_by_name": s.created_by_name,
        "created_at": to_tehran(s.created_at).isoformat() if s.created_at else None,
        "created_at_display": _stamp(s.created_at),
    }


# ---------------------------------------------------------------------
# Sales: list / get
# ---------------------------------------------------------------------
_SORTS = {
    "date": CrmSale.sale_date, "amount": CrmSale.amount, "quantity_kg": CrmSale.quantity_kg,
    "created_at": CrmSale.created_at,
}


def list_sales(actor: User, *, page: int, per_page: int, filters: SaleFilters, sort: str = "-date"):
    _require(actor, "sale", "read")
    query = _apply(_base_query(CrmSale), filters)
    desc = sort.startswith("-")
    column = _SORTS.get(sort.lstrip("-"), CrmSale.sale_date)
    query = query.order_by(column.desc() if desc else column.asc(), CrmSale.id.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total


def get_sale(actor: User, sale_id: int) -> CrmSale:
    _require(actor, "sale", "read")
    return _get_sale_or_404(sale_id)


def _get_sale_or_404(sale_id: int) -> CrmSale:
    sale = db.session.get(CrmSale, sale_id)
    if sale is None or sale.deleted_at is not None:
        raise NotFoundError(f"Sale {sale_id} was not found.")
    return sale


# ---------------------------------------------------------------------
# Sales: write
# ---------------------------------------------------------------------
def _customer_or_error(customer_id: int) -> Customer:
    customer = db.session.get(Customer, customer_id)
    if customer is None or customer.deleted_at is not None:
        raise ConflictError(f"Customer {customer_id} does not exist in the customer bank.")
    return customer


def _product_or_error(product_id: int) -> CustomerOptionItem:
    """What a sale sells is a GRADE: an entry of the customer bank's grade pick-list (kind=GRADE)."""
    product = db.session.get(CustomerOptionItem, product_id)
    if product is None or product.kind != OptionKind.GRADE or not product.is_active:
        raise ConflictError(f"Grade {product_id} is not available in the customer bank's grade list.")
    return product


def _payment_or_error(payment_id: int) -> CrmPaymentMethod:
    method = db.session.get(CrmPaymentMethod, payment_id)
    if method is None or not method.is_active:
        raise ConflictError(f"Payment method {payment_id} is not available.")
    return method


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(_MONEY, rounding=ROUND_HALF_UP)


def _compute_amount(quantity, unit_price) -> Decimal:
    return _money(Decimal(str(quantity)) * Decimal(str(unit_price)))


def _set_date(sale: CrmSale, value) -> None:
    d = parse_date_input(value) if value else tehran_today()
    sale.sale_date = d
    sale.jalali_year, sale.jalali_month, _ = to_jalali(d)


def sync_customer_purchase_dates(customer_ids) -> None:
    """Keeps the customer file's first/last purchase date (step 4 of the wizard) equal to what the
    sales actually say. A customer with no invoices left keeps whatever was typed by hand."""
    for cid in {c for c in customer_ids if c}:
        first, last = (
            db.session.query(db.func.min(CrmSale.sale_date), db.func.max(CrmSale.sale_date))
            .filter(
                CrmSale.customer_id == cid, CrmSale.deleted_at.is_(None),
                CrmSale.document_type == DocumentType.INVOICE,
            ).one()
        )
        customer = db.session.get(Customer, cid)
        if customer is not None and first is not None:
            customer.first_purchase_date = first
            customer.last_purchase_date = last


def create_sale(actor: User, payload: SaleCreate, *, ip_address: str | None = None) -> CrmSale:
    _require(actor, "sale", "create")
    customer = _customer_or_error(payload.customer_id)
    product = _product_or_error(payload.product_id)
    method = _payment_or_error(payload.payment_method_id) if payload.payment_method_id else None

    sale = CrmSale(
        customer=customer, product=product, payment_method=method,
        quantity_kg=payload.quantity_kg, unit_price=payload.unit_price,
        amount=_money(payload.amount) if payload.amount is not None
        else _compute_amount(payload.quantity_kg, payload.unit_price),
        sale_type=payload.sale_type, document_type=payload.document_type, status=payload.status,
        description=payload.description, created_by_user_id=actor.id,
    )
    _set_date(sale, payload.date)
    db.session.add(sale)
    db.session.flush()
    sync_customer_purchase_dates([customer.id])
    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type="sale", entity_id=sale.id,
        metadata={"customer_id": customer.id, "amount": float(sale.amount), "date": format_jalali(sale.sale_date)},
        ip_address=ip_address,
    )
    db.session.commit()
    return sale


def update_sale(actor: User, sale_id: int, payload: SaleUpdate, *, ip_address: str | None = None) -> CrmSale:
    _require(actor, "sale", "update")
    sale = _get_sale_or_404(sale_id)
    changes = payload.model_dump(exclude_unset=True)
    old_customer = sale.customer_id

    if "customer_id" in changes and changes["customer_id"] is not None:
        sale.customer = _customer_or_error(changes["customer_id"])
    if "product_id" in changes and changes["product_id"] is not None:
        sale.product = _product_or_error(changes["product_id"])
    if changes.get("clear_payment_method"):
        sale.payment_method = None
    elif changes.get("payment_method_id") is not None:
        sale.payment_method = _payment_or_error(changes["payment_method_id"])

    quantity_or_price_changed = False
    if changes.get("quantity_kg") is not None:
        sale.quantity_kg = changes["quantity_kg"]
        quantity_or_price_changed = True
    if changes.get("unit_price") is not None:
        sale.unit_price = changes["unit_price"]
        quantity_or_price_changed = True
    if changes.get("amount") is not None:
        sale.amount = _money(changes["amount"])  # an explicit total always wins
    elif quantity_or_price_changed:
        sale.amount = _compute_amount(sale.quantity_kg, sale.unit_price)

    for field in ("sale_type", "document_type", "status"):
        if changes.get(field) is not None:
            setattr(sale, field, changes[field])
    if "description" in changes:
        sale.description = changes["description"]
    if changes.get("date"):
        _set_date(sale, changes["date"])

    db.session.flush()
    sync_customer_purchase_dates([old_customer, sale.customer_id])
    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type="sale", entity_id=sale.id,
        metadata={"fields": sorted(changes)}, ip_address=ip_address,
    )
    db.session.commit()
    return sale


def delete_sale(actor: User, sale_id: int, *, ip_address: str | None = None) -> None:
    _require(actor, "sale", "delete")
    sale = _get_sale_or_404(sale_id)
    sale.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.flush()
    sync_customer_purchase_dates([sale.customer_id])
    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type="sale", entity_id=sale.id,
        metadata={"customer_id": sale.customer_id}, ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Customer picker (reads the customer bank)
# ---------------------------------------------------------------------
def lookup_customers(actor: User, *, search: str = "", limit: int = 20, customer_id: int | None = None) -> list[dict]:
    """id + name only, for the sale form / filters. Gated by crm.sale.read so sales staff can pick a
    customer without needing the full customer-file permission."""
    _require(actor, "sale", "read")
    query = db.session.query(Customer).filter(Customer.deleted_at.is_(None))
    if customer_id:  # resolve one customer by its bank id (deep links such as /crm/sales?customer_id=7)
        return [_customer_ref(c) for c in query.filter(Customer.id == customer_id).all()]
    query = query.filter(Customer.is_active.is_(True))
    match = _customer_text_match(search.strip())
    if match is not None:
        query = query.filter(match)
    rows = query.order_by(Customer.company_name, Customer.last_name, Customer.id).limit(max(1, min(limit, 100))).all()
    return [_customer_ref(c) for c in rows]


def sales_filter_options(actor: User) -> dict:
    """Province / industry values come from the customer bank itself (no separate lookup tables)."""
    _require(actor, "sale", "read")
    base = db.session.query(Customer).filter(Customer.deleted_at.is_(None))
    provinces = [r[0] for r in base.filter(Customer.factory_province.isnot(None)).with_entities(
        Customer.factory_province).distinct().order_by(Customer.factory_province)]
    industries = [r[0] for r in base.filter(Customer.category.isnot(None)).with_entities(
        Customer.category).distinct().order_by(Customer.category)]
    years = [r[0] for r in db.session.query(CrmSale.jalali_year).filter(CrmSale.deleted_at.is_(None))
             .distinct().order_by(CrmSale.jalali_year.desc())]
    return {"provinces": provinces, "industries": industries, "years": years, "presets": list(PRESETS)}


# ---------------------------------------------------------------------
# Analytics (same filters as the list, aggregated in SQL)
# ---------------------------------------------------------------------
def _top_n(rows: list[dict], n: int, key: str = "amount") -> list[dict]:
    rows = sorted(rows, key=lambda r: r[key], reverse=True)
    top = rows[:n]
    rest = rows[n:]
    if rest:
        top.append({
            "id": None, "name": "سایر",
            "amount": sum(r["amount"] for r in rest), "quantity_kg": sum(r["quantity_kg"] for r in rest),
        })
    return top


def _grouped(filters: SaleFilters, group_col, *, with_id: bool = False) -> list[dict]:
    amount, qty = _signed(CrmSale.amount), _signed(CrmSale.quantity_kg)
    cols = [group_col, db.func.sum(amount), db.func.sum(qty)]
    q = _apply(_base_query(*cols), filters).group_by(group_col)
    return [
        {"key": r[0], "amount": float(r[1] or 0), "quantity_kg": float(r[2] or 0)} for r in q.all()
    ]


def analytics(actor: User, filters: SaleFilters, *, top: int = 8) -> dict:
    _require(actor, "sale", "read")
    amount, qty = _signed(CrmSale.amount), _signed(CrmSale.quantity_kg)

    totals = _apply(_base_query(
        db.func.coalesce(db.func.sum(amount), 0), db.func.coalesce(db.func.sum(qty), 0),
        db.func.count(CrmSale.id), db.func.count(db.func.distinct(CrmSale.customer_id)),
        db.func.sum(db.case((CrmSale.document_type == DocumentType.RETURN, 1), else_=0)),
    ), filters).one()
    net_amount, net_qty = float(totals[0] or 0), float(totals[1] or 0)
    doc_count, customer_count, return_count = int(totals[2] or 0), int(totals[3] or 0), int(totals[4] or 0)
    invoice_count = doc_count - return_count

    # customers (resolve names once from the bank)
    by_customer_rows = _grouped(filters, CrmSale.customer_id)
    names = {}
    if by_customer_rows:
        ids = [r["key"] for r in by_customer_rows]
        for c in db.session.query(Customer).filter(Customer.id.in_(ids)).all():
            names[c.id] = customer_label(c)
    by_customer = [{"id": r["key"], "name": names.get(r["key"], f"#{r['key']}"),
                    "amount": r["amount"], "quantity_kg": r["quantity_kg"]} for r in by_customer_rows]

    prod_names = {
        p.id: p.name for p in db.session.query(CustomerOptionItem)
    }
    by_product = [{"id": r["key"], "name": prod_names.get(r["key"], f"#{r['key']}"),
                   "amount": r["amount"], "quantity_kg": r["quantity_kg"]}
                  for r in _grouped(filters, CrmSale.product_id)]

    pay_names = {p.id: p.name for p in db.session.query(CrmPaymentMethod).all()}
    by_payment = [{"id": r["key"], "name": pay_names.get(r["key"], "نامشخص"),
                   "amount": r["amount"], "quantity_kg": r["quantity_kg"]}
                  for r in _grouped(filters, CrmSale.payment_method_id)]

    sale_type_label = {"OFFICIAL": "رسمی", "UNOFFICIAL": "غیررسمی"}
    by_sale_type = [{"id": r["key"].value if hasattr(r["key"], "value") else r["key"],
                     "name": sale_type_label.get(r["key"].value if hasattr(r["key"], "value") else r["key"], "—"),
                     "amount": r["amount"], "quantity_kg": r["quantity_kg"]}
                    for r in _grouped(filters, CrmSale.sale_type)]

    def _named(rows):
        return [{"id": None, "name": r["key"] or "نامشخص", "amount": r["amount"], "quantity_kg": r["quantity_kg"]}
                for r in rows]

    by_province = _named(_grouped(filters, Customer.factory_province))
    by_industry = _named(_grouped(filters, Customer.category))

    # timeline: grouped on the stored Jalali year/month, gaps filled so the chart axis is continuous
    amount_col = db.func.sum(amount)
    qty_col = db.func.sum(qty)
    cnt_col = db.func.count(CrmSale.id)
    month_rows = (
        _apply(_base_query(CrmSale.jalali_year, CrmSale.jalali_month, amount_col, qty_col, cnt_col), filters)
        .group_by(CrmSale.jalali_year, CrmSale.jalali_month)
        .order_by(CrmSale.jalali_year, CrmSale.jalali_month).all()
    )
    found = {(r[0], r[1]): (float(r[2] or 0), float(r[3] or 0), int(r[4] or 0)) for r in month_rows}
    monthly = []
    if found:
        (y0, m0), (y1, m1) = min(found), max(found)
        y, m = y0, m0
        while (y, m) <= (y1, m1) and len(monthly) < 120:
            a, k, n = found.get((y, m), (0.0, 0.0, 0))
            monthly.append({"year": y, "month": m, "label": f"{MONTH_NAMES[m - 1]} {y}",
                            "short_label": MONTH_NAMES[m - 1], "amount": a, "quantity_kg": k, "count": n})
            m += 1
            if m > 12:
                y, m = y + 1, 1
    yearly_map: dict[int, dict] = {}
    for row in monthly:
        e = yearly_map.setdefault(row["year"], {"year": row["year"], "amount": 0.0, "quantity_kg": 0.0, "count": 0})
        e["amount"] += row["amount"]
        e["quantity_kg"] += row["quantity_kg"]
        e["count"] += row["count"]
    yearly = [yearly_map[y] for y in sorted(yearly_map)]

    top_customer = max(by_customer, key=lambda r: r["amount"], default=None)
    top_product = max(by_product, key=lambda r: r["quantity_kg"], default=None)
    return {
        "filters": filters.as_dict(),
        "kpis": {
            "net_amount": net_amount, "net_quantity_kg": net_qty, "document_count": doc_count,
            "invoice_count": invoice_count, "return_count": return_count, "customer_count": customer_count,
            "avg_invoice": (net_amount / invoice_count) if invoice_count else 0,
            "top_customer": top_customer, "top_product": top_product,
        },
        "monthly": monthly, "yearly": yearly,
        "by_product": _top_n(by_product, top), "by_product_quantity": _top_n(
            [dict(r) for r in by_product], top, key="quantity_kg"),
        "by_customer": _top_n(by_customer, 6), "by_sale_type": by_sale_type, "by_payment": by_payment,
        "by_province": _top_n(by_province, top), "by_industry": _top_n(by_industry, top),
    }


# ---------------------------------------------------------------------
# Products (read-only view of the customer bank's pick-list) & payment methods
# ---------------------------------------------------------------------
def list_products(actor: User, *, include_inactive: bool = False) -> list[dict]:
    """The customer bank's GRADE pick-list (what the sale form calls 'product' in its API fields).
    There is no CRM-side table, so nothing here can drift from the customer bank: add / rename /
    remove a grade there."""
    _require_any_read(actor)
    q = db.session.query(CustomerOptionItem).filter(CustomerOptionItem.kind == OptionKind.GRADE)
    if not include_inactive:
        q = q.filter(CustomerOptionItem.is_active.is_(True))
    return [
        {"id": o.id, "name": o.name, "is_active": o.is_active}
        for o in q.order_by(CustomerOptionItem.sort_order, CustomerOptionItem.name, CustomerOptionItem.id).all()
    ]


def _dump_method(m: CrmPaymentMethod, sales_count: int | None = None) -> dict:
    if sales_count is None:
        sales_count = _method_sales_count(m.id)
    return {"id": m.id, "name": m.name, "is_active": m.is_active, "sales_count": sales_count}


def _method_sales_count(method_id: int) -> int:
    return (
        db.session.query(db.func.count(CrmSale.id))
        .filter(CrmSale.payment_method_id == method_id, CrmSale.deleted_at.is_(None)).scalar() or 0
    )


def list_payment_methods(actor: User, *, include_inactive: bool = False) -> list[dict]:
    _require_any_read(actor)
    q = db.session.query(CrmPaymentMethod)
    if not include_inactive:
        q = q.filter(CrmPaymentMethod.is_active.is_(True))
    counts = dict(
        db.session.query(CrmSale.payment_method_id, db.func.count(CrmSale.id))
        .filter(CrmSale.payment_method_id.isnot(None), CrmSale.deleted_at.is_(None))
        .group_by(CrmSale.payment_method_id).all()
    )
    return [_dump_method(m, int(counts.get(m.id, 0))) for m in q.order_by(CrmPaymentMethod.name, CrmPaymentMethod.id).all()]


def create_payment_method(actor: User, payload: PaymentMethodIn, *, ip_address: str | None = None) -> dict:
    _require(actor, "product", "create")
    if db.session.query(CrmPaymentMethod.id).filter(CrmPaymentMethod.name == payload.name).first():
        raise ConflictError("This payment method already exists.")
    method = CrmPaymentMethod(name=payload.name)
    db.session.add(method)
    db.session.flush()
    write_audit_log(user_id=actor.id, action="create", module=MODULE, entity_type="payment_method",
                    entity_id=method.id, ip_address=ip_address)
    db.session.commit()
    return _dump_method(method)


def update_payment_method(actor: User, method_id: int, payload: PaymentMethodUpdate,
                          *, ip_address: str | None = None) -> dict:
    _require(actor, "product", "update")
    method = db.session.get(CrmPaymentMethod, method_id)
    if method is None:
        raise NotFoundError(f"Payment method {method_id} was not found.")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name") and db.session.query(CrmPaymentMethod.id).filter(
        CrmPaymentMethod.name == changes["name"], CrmPaymentMethod.id != method_id
    ).first():
        raise ConflictError("This payment method already exists.")
    for field, value in changes.items():
        if value is not None:
            setattr(method, field, value)
    write_audit_log(user_id=actor.id, action="update", module=MODULE, entity_type="payment_method",
                    entity_id=method.id, metadata={"fields": sorted(changes)}, ip_address=ip_address)
    db.session.commit()
    return _dump_method(method)


def delete_payment_method(actor: User, method_id: int, *, force: bool = False, ip_address: str | None = None) -> None:
    """Removes a payment method.

    Unused methods are simply deleted. A method that recorded sales point at is refused (409) unless
    `force` is set: then those sales are detached (they show "نامشخص" -- nothing else about them
    changes, the column is nullable) and the method is deleted. The UI asks the user to confirm that
    explicitly, using the `sales_count` the list returns."""
    _require(actor, "product", "delete")
    method = db.session.get(CrmPaymentMethod, method_id)
    if method is None:
        raise NotFoundError(f"Payment method {method_id} was not found.")
    # Count ALL rows (soft-deleted sales still hold the foreign key).
    used_by = db.session.query(db.func.count(CrmSale.id)).filter(CrmSale.payment_method_id == method_id).scalar() or 0
    if used_by and not force:
        raise ConflictError(
            f"This payment method is used by {used_by} recorded sale(s). Confirm to remove it anyway; "
            "those sales will be left without a payment method."
        )
    if used_by:
        db.session.query(CrmSale).filter(CrmSale.payment_method_id == method_id).update(
            {CrmSale.payment_method_id: None}, synchronize_session=False
        )
    db.session.delete(method)
    write_audit_log(user_id=actor.id, action="delete", module=MODULE, entity_type="payment_method",
                    entity_id=method_id, metadata={"detached_sales": used_by}, ip_address=ip_address)
    db.session.commit()


# ---------------------------------------------------------------------
# Spreadsheet import (customers must already exist in the bank)
# ---------------------------------------------------------------------
def import_sales(actor: User, payload: ImportRequest, *, ip_address: str | None = None) -> dict:
    _require(actor, "sale", "create")

    # name -> customers, built once from the customer bank
    index: dict[str, set[int]] = {}
    for c in db.session.query(Customer).filter(Customer.deleted_at.is_(None)).all():
        for n in _customer_names(c):
            index.setdefault(n, set()).add(c.id)

    # Grades come from the customer bank's grade list only -- an unknown name is a rejected row,
    # exactly like an unknown customer (importing must never create a second product list).
    products = {
        normalize_name(p.name): p
        for p in db.session.query(CustomerOptionItem).filter(
            CustomerOptionItem.kind == OptionKind.GRADE, CustomerOptionItem.is_active.is_(True)
        )
    }
    methods = {normalize_name(m.name): m for m in db.session.query(CrmPaymentMethod).all()}

    created, errors, touched = 0, [], set()
    for i, row in enumerate(payload.rows, start=1):
        ids = index.get(normalize_name(row.customer), set())
        if not ids:
            errors.append({"row": i, "customer": row.customer,
                           "message": "Customer was not found in the customer bank."})
            continue
        if len(ids) > 1:
            errors.append({"row": i, "customer": row.customer,
                           "message": "More than one customer in the bank has this name."})
            continue
        product = products.get(normalize_name(row.product))
        if product is None:
            errors.append({"row": i, "customer": row.customer,
                           "message": f"Grade '{row.product}' was not found in the customer bank's grade list."})
            continue
        if row.amount in (None, 0) and not row.unit_price:
            errors.append({"row": i, "customer": row.customer, "message": "Amount or unit price is required."})
            continue
        if payload.dry_run:
            created += 1
            continue

        method = methods.get(normalize_name(row.payment)) if row.payment else None
        unit_price = row.unit_price
        if not unit_price and row.amount and row.quantity_kg:
            unit_price = (row.amount / row.quantity_kg).quantize(_MONEY, rounding=ROUND_HALF_UP)
        sale = CrmSale(
            customer_id=next(iter(ids)), product=product, payment_method=method,
            quantity_kg=row.quantity_kg, unit_price=unit_price,
            amount=_money(row.amount) if row.amount else _compute_amount(row.quantity_kg, unit_price),
            sale_type=row.sale_type, document_type=row.document_type, status=row.status,
            description=row.description, created_by_user_id=actor.id,
        )
        _set_date(sale, row.date)
        db.session.add(sale)
        touched.add(sale.customer_id)
        created += 1

    if not payload.dry_run and created:
        db.session.flush()
        sync_customer_purchase_dates(touched)
        write_audit_log(user_id=actor.id, action="import", module=MODULE, entity_type="sale",
                        metadata={"created": created, "rejected": len(errors)}, ip_address=ip_address)
        db.session.commit()
    return {"created": created, "rejected": len(errors), "errors": errors[:200], "dry_run": payload.dry_run}
