"""
Service layer for /api/customers -- CRM module.

Same pattern as modules/suppliers/services.py: permission checks live here, not in
routes.py. Customers are a single, un-scoped business resource, so every check is
GLOBAL-only (`crm.customer.<read|create|update|delete>`, already declared in
app/permissions/registry.py). There is no public/unauthenticated entry point.
"""
import datetime as dt
import json
from datetime import datetime, timezone

from app.core import request_ops
from app.modules.notifications import services as notifications
from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.customers.models import (
    AcquaintanceSource, ActivityType, CommercialStatus, CreditRating, Customer, CustomerCategory, CustomerType,
    OperationalStatus, OptionKind, CustomerOptionItem, PaymentType,
)
from app.modules.customers.schemas import (
    CategoryIn, CategoryUpdate, CustomerCreate, CustomerUpdate, Industry, OptionItemIn, OptionItemUpdate,
    _dedupe_industries, check_identity,
)
from app.modules.suppliers.models import Supplier
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "crm"
ENTITY_TYPE = "customer"

# JSON-column fields: dumped in JSON mode (dates -> ISO strings) so they can be stored.
_JSON_FIELDS = (
    "contacts", "industries", "produced_products", "consumed_products", "current_suppliers", "contact_log",
    "production_line_names", "production_line_counts",
)
# Identity fields that only apply to one customer type.
_INDIVIDUAL_ONLY = ("first_name", "last_name", "national_id", "brand_name")
_LEGAL_ONLY = ("company_name", "company_national_id", "registration_number", "economic_id", "activity_start_date", "company_phone")


LINK = "/crm/customers"


def _link(customer) -> str:
    """Where a notification about this record leads: the customer bank, with the file opened."""
    return f"{LINK}?open={customer.id}"


def _can(actor: User, action: str) -> bool:
    return has_permission(actor, f"crm.customer.{action}", None, None)


def viewer_flags(actor: User, customer: "Customer") -> dict:
    """What THIS user may do with the record (the UI shows buttons from this; the server re-checks)."""
    return request_ops.viewer_flags(customer, actor.id, can_update=_can(actor, "update"), can_review=_can(actor, "review"))


def _require(actor: User, action: str) -> None:
    key = f"crm.customer.{action}"
    if not has_permission(actor, key, None, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _get_or_404(customer_id: int) -> Customer:
    customer = db.session.get(Customer, customer_id)
    if customer is None or customer.deleted_at is not None:
        raise NotFoundError(f"Customer {customer_id} was not found.")
    return customer


# ---------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------
_AR_TO_FA = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_FA_TO_AR = str.maketrans({"ی": "ي", "ک": "ك"})
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _json_match(column, term: str, paths: tuple[str, ...]):
    """Some element of a JSON-array column matches `term` in one of `paths`.
    MySQL: JSON_SEARCH on exactly those keys. Other dialects (the SQLite test
    DB): a text scan of the whole column."""
    escaped = _escape_like(term)
    if db.engine.dialect.name == "mysql":
        return db.func.json_search(column, "one", f"%{escaped}%", None, *paths).isnot(None)
    # Text scan. SQLite stores JSON with non-ASCII escaped (\u06af...), so match that form too.
    text = db.func.lower(db.cast(column, db.Text))
    ascii_form = _escape_like(json.dumps(term)[1:-1].lower())
    return db.or_(
        text.like(f"%{escaped.lower()}%", escape="\\"),
        text.like(f"%{ascii_form}%", escape="\\"),
    )


def _search_condition(term: str):
    """Free text over names, ids, places, contact people/numbers, and the
    produced / consumed products and current suppliers. Text is matched in both
    Persian (ی ک) and Arabic (ي ك) spellings; digits in Latin form."""
    persian = term.translate(_AR_TO_FA)
    variants = {term, persian, persian.translate(_FA_TO_AR)}
    latin = term.translate(_DIGITS)

    conditions = [
        Customer.national_id.like(f"%{latin}%"),
        Customer.company_national_id.like(f"%{latin}%"),
        Customer.registration_number.like(f"%{latin}%"),
        Customer.economic_id.like(f"%{latin}%"),
        Customer.head_office_postal_code.like(f"%{latin}%"),
        Customer.factory_postal_code.like(f"%{latin}%"),
        _json_match(Customer.contacts, latin, ("$[*].mobile", "$[*].landline")),
    ]
    for v in variants:
        like = f"%{v.lower()}%"
        conditions += [
            db.func.lower(Customer.company_name).like(like),
            db.func.lower(Customer.first_name).like(like),
            db.func.lower(Customer.last_name).like(like),
            db.func.lower(Customer.brand_name).like(like),
            db.func.lower(Customer.factory_city).like(like),
            db.func.lower(Customer.factory_province).like(like),
            _json_match(Customer.contacts, v, ("$[*].first_name", "$[*].last_name", "$[*].email")),
            _json_match(Customer.produced_products, v, ("$[*].name",)),
            _json_match(Customer.consumed_products, v, ("$[*].name", "$[*].grade_specs")),
            _json_match(Customer.current_suppliers, v, ("$[*].name",)),
            _json_match(Customer.production_line_names, v, ("$[*]",)),
        ]
    return db.or_(*conditions)


def _industry_condition(category: str, subcategory: str):
    """Some industry of the customer matches (a customer can have several).
    MySQL/MariaDB: JSON_SEARCH on the exact keys (MariaDB's JSON_CONTAINS does not match an
    object inside an array). Other dialects (SQLite tests): match the stored JSON text."""
    if db.engine.dialect.name == "mysql":
        conds = []
        if category:
            conds.append(db.func.json_search(
                Customer.industries, "one", category, None, "$[*].category").isnot(None))
        if subcategory:
            conds.append(db.func.json_search(
                Customer.industries, "one", subcategory, None, "$[*].subcategory").isnot(None))
        return db.and_(*conds)
    parts = []
    if category:
        parts.append(f'"category": {json.dumps(category)}')
    if subcategory:
        parts.append(f'"subcategory": {json.dumps(subcategory)}')
    text = db.cast(Customer.industries, db.Text)
    return text.like(f"%{_escape_like(', '.join(parts))}%", escape="\\")


_SORTS = {
    # By industry = the customer's first (primary) industry, mirrored in category / subcategory.
    # Customers without an industry always come last.
    "category": [Customer.category.is_(None), Customer.category.asc(), Customer.subcategory.is_(None),
                 Customer.subcategory.asc(), Customer.id.desc()],
    "-category": [Customer.category.is_(None), Customer.category.desc(), Customer.subcategory.is_(None),
                  Customer.subcategory.desc(), Customer.id.desc()],
    "-created_at": [Customer.id.desc()],
    "created_at": [Customer.id.asc()],
    "next_follow_up_date": [Customer.next_follow_up_date.is_(None), Customer.next_follow_up_date.asc(), Customer.id.desc()],
    "-last_negotiation_date": [Customer.last_negotiation_date.is_(None), Customer.last_negotiation_date.desc(), Customer.id.desc()],
    "-last_purchase_date": [Customer.last_purchase_date.is_(None), Customer.last_purchase_date.desc(), Customer.id.desc()],
}


def list_customers(
    actor: User, *, page: int, per_page: int, search: str = "", category: str = "", subcategory: str = "",
    commercial_statuses: list[str] | None = None, operational_status: str = "", customer_type: str = "",
    province: str = "", city: str = "", activity_type: str = "", assigned_to: str = "", credit_rating: str = "",
    follow_up_due: bool = False, is_finalized: bool | None = None, include_inactive: bool = False,
    sort: str = "-created_at", review_status: str = "",
):
    _require(actor, "read")

    query = db.session.query(Customer).filter(Customer.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(Customer.is_active.is_(True))
    if category or subcategory:
        query = query.filter(_industry_condition(category, subcategory))
    if credit_rating in {r.value for r in CreditRating}:
        query = query.filter(Customer.credit_rating == credit_rating)
    valid = {s.value for s in CommercialStatus}
    wanted = [s for s in (commercial_statuses or []) if s in valid]
    if wanted:
        query = query.filter(Customer.commercial_status.in_(wanted))
    if operational_status in {s.value for s in OperationalStatus}:
        query = query.filter(Customer.operational_status == operational_status)
    if customer_type in {t.value for t in CustomerType}:
        query = query.filter(Customer.customer_type == customer_type)
    if province:
        query = query.filter(Customer.factory_province == province)
    if city:
        query = query.filter(Customer.factory_city == city)
    if activity_type in {a.value for a in ActivityType}:
        query = query.filter(Customer.activity_types_csv.like(f"%{activity_type}%"))
    if assigned_to == "none":
        query = query.filter(Customer.assigned_to_user_id.is_(None))
    elif assigned_to.isdigit():
        query = query.filter(Customer.assigned_to_user_id == int(assigned_to))
    if is_finalized is not None:
        query = query.filter(Customer.is_finalized.is_(is_finalized))
    if review_status in ("PENDING", "APPROVED", "REJECTED", "NEEDS_EDIT"):
        query = query.filter(Customer.review_status == review_status)
        if review_status == "PENDING":  # the review queue: submitted requests only, not drafts
            query = query.filter(Customer.is_finalized.is_(True))
    if follow_up_due:
        query = query.filter(
            Customer.next_follow_up_date.isnot(None),
            Customer.next_follow_up_date <= dt.date.today(),
            Customer.commercial_status != CommercialStatus.INACTIVE_LOST,
            Customer.operational_status == OperationalStatus.ACTIVE,
        )
    if search and search.strip():
        query = query.filter(_search_condition(search.strip()))

    query = query.order_by(*_SORTS.get(sort, _SORTS["-created_at"]))
    return paginate_query(query, page, per_page)


def customer_stats(actor: User) -> dict:
    """Counts for dashboard cards / filter badges."""
    _require(actor, "read")
    base = db.session.query(Customer).filter(Customer.deleted_at.is_(None), Customer.is_active.is_(True))

    by_commercial = {s.value: 0 for s in CommercialStatus}
    for status, n in base.with_entities(Customer.commercial_status, db.func.count(Customer.id)).group_by(
        Customer.commercial_status
    ):
        by_commercial[status.value if hasattr(status, "value") else status] = n
    by_operational = {s.value: 0 for s in OperationalStatus}
    for status, n in base.with_entities(Customer.operational_status, db.func.count(Customer.id)).group_by(
        Customer.operational_status
    ):
        by_operational[status.value if hasattr(status, "value") else status] = n

    due = base.filter(
        Customer.next_follow_up_date.isnot(None), Customer.next_follow_up_date <= dt.date.today(),
        Customer.commercial_status != CommercialStatus.INACTIVE_LOST,
        Customer.operational_status == OperationalStatus.ACTIVE,
    ).count()
    return {
        "total": base.count(),
        "by_commercial_status": by_commercial,
        "by_operational_status": by_operational,
        "follow_up_due": due,
        "unassigned": base.filter(Customer.assigned_to_user_id.is_(None)).count(),
        "not_finalized": base.filter(Customer.is_finalized.is_(False)).count(),
        "pending_review": base.filter(Customer.review_status == "PENDING", Customer.is_finalized.is_(True)).count(),
    }


def list_locations(actor: User) -> list[dict]:
    """[{province, count, cities: [{city, count}]}] -- feeds the province/city filter."""
    _require(actor, "read")
    rows = (
        db.session.query(Customer.factory_province, Customer.factory_city, db.func.count(Customer.id))
        .filter(Customer.deleted_at.is_(None), Customer.factory_province.isnot(None))
        .group_by(Customer.factory_province, Customer.factory_city)
        .order_by(Customer.factory_province, Customer.factory_city)
        .all()
    )
    out: dict[str, dict] = {}
    for province, city, n in rows:
        p = out.setdefault(province, {"province": province, "count": 0, "cities": []})
        p["count"] += n
        if city:
            p["cities"].append({"city": city, "count": n})
    return list(out.values())


def list_assignable_users(actor: User) -> list[dict]:
    """Active staff the "مسئول پیگیری" select may offer. Gated by crm.customer.read (not
    core.user.read), so a CRM employee can pick an assignee without user-management access."""
    _require(actor, "read")
    rows = (
        db.session.query(User.id, User.full_name)
        .filter(User.deleted_at.is_(None), User.is_active.is_(True))
        .order_by(User.full_name, User.id).all()
    )
    return [{"id": r[0], "full_name": r[1]} for r in rows]


def get_customer(actor: User, customer_id: int) -> Customer:
    _require(actor, "read")
    return _get_or_404(customer_id)


# ---------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------
def _resolve_assignee(user_id: int | None) -> None:
    if user_id is None:
        return
    user = db.session.get(User, user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise ConflictError(f"User {user_id} is not available for assignment.")


def _resolve_current_suppliers(rows: list[dict]) -> list[dict]:
    """A link must point at a real supplier; the stored name then comes from it."""
    out = []
    for row in rows:
        sid = row.get("supplier_id")
        grades = row.get("grades") or []
        if sid:
            supplier = db.session.get(Supplier, sid)
            if supplier is None or supplier.deleted_at is not None:
                raise ConflictError(f"Supplier {sid} was not found.")
            out.append({"name": supplier.display_name, "supplier_id": supplier.id, "grades": grades})
        else:
            out.append({"name": row["name"], "supplier_id": None, "grades": grades})
    return out


def _derive_contact_log(customer: Customer) -> None:
    """Keep the log date-ordered and `first_contact_date` = its earliest entry."""
    log = sorted(customer.contact_log or [], key=lambda e: e["date"])
    customer.contact_log = log
    customer.first_contact_date = dt.date.fromisoformat(log[0]["date"]) if log else None


_KG_PER_TON = 1000


def _derive_capacity(customer: Customer) -> None:
    """ظرفیت تولید کارخانه (tons per year) = sum of the produced products' yearly amounts;
    kilograms are converted to tons. No amount at all -> None."""
    total_kg, any_amount = 0, False
    for p in customer.produced_products or []:
        amount = p.get("amount")
        if amount is None:
            continue
        any_amount = True
        total_kg += amount * _KG_PER_TON if p.get("unit", "TON") != "KG" else amount
    customer.production_capacity = round(total_kg / _KG_PER_TON, 3) if any_amount else None


def _check_merged(customer: Customer) -> None:
    """Cross-field rules on the *merged* row (a PATCH only carries part of it)."""
    fp, lp = customer.first_purchase_date, customer.last_purchase_date
    if fp and lp and lp < fp:
        raise ConflictError("Last purchase date cannot be before the first purchase date.")

    # نام خطوط تولید: a free list the user adds to / removes from by hand. The line count is
    # not an input any more -- it simply follows the number of names. (A legacy count with no
    # names is left alone; clients clear it by sending production_lines_count: null.)
    names = customer.production_line_names or []
    if names:
        # units per line (default 1) stay parallel to the names; the total is their sum
        counts = [int(n) for n in (customer.production_line_counts or [])][: len(names)]
        counts += [1] * (len(names) - len(counts))
        customer.production_line_counts = counts
        customer.production_lines_count = sum(counts)
    else:
        customer.production_line_names = []
        customer.production_line_counts = []

    # نام شرکت یا برند belongs to individual customers only.
    if customer.customer_type == CustomerType.LEGAL:
        customer.brand_name = None

    # منبع آشنایی: the free text belongs to 'Other' only.
    if customer.acquaintance_source != AcquaintanceSource.OTHER:
        customer.acquaintance_source_other = None
    elif not customer.acquaintance_source_other:
        raise ConflictError("Describe the acquaintance source when choosing 'Other'.")

    # شرایط پرداخت: a credit duration (1-12 months, or free text for 'Other') only for credit types.
    if customer.payment_type in (PaymentType.CREDIT, PaymentType.CASH_CREDIT):
        if customer.credit_other:
            customer.credit_months = None
        elif not customer.credit_months:
            raise ConflictError("Credit duration (1-12 months or other) is required for credit payments.")
    else:
        customer.credit_months = None
        customer.credit_other = None


def _check_category(
    category: str | None, subcategory: str | None = None, *,
    keep_category: str | None = None, keep_subcategory: str | None = None,
) -> None:
    """The industry must be an active admin-managed main category and the
    sub-category an active child of it. `keep_*` lets an edit save a customer
    whose existing (renamed/removed) values are unchanged."""
    if subcategory and not category:
        raise ConflictError("Pick an industry before choosing a sub-category.")
    parent = None
    if category and category != keep_category:
        parent = db.session.query(CustomerCategory).filter(
            CustomerCategory.name == category, CustomerCategory.parent_id.is_(None),
            CustomerCategory.is_active.is_(True),
        ).first()
        if parent is None:
            raise ConflictError(f"Industry '{category}' is not available. Please pick one from the list.")
    if subcategory and not (subcategory == keep_subcategory and category == keep_category):
        if parent is None:
            parent = db.session.query(CustomerCategory).filter(
                CustomerCategory.name == category, CustomerCategory.parent_id.is_(None)
            ).first()
        ok = parent is not None and db.session.query(CustomerCategory.id).filter(
            CustomerCategory.parent_id == parent.id, CustomerCategory.name == subcategory,
            CustomerCategory.is_active.is_(True),
        ).first()
        if not ok:
            raise ConflictError(f"Sub-category '{subcategory}' is not available under '{category}'.")


def _industries_of(customer: Customer) -> list[dict]:
    """The customer's industries; falls back to the mirrored single category for a row that has none."""
    rows = [dict(i) for i in (customer.industries or [])]
    if not rows and customer.category:
        rows = [{"category": customer.category, "subcategory": customer.subcategory}]
    return rows


def _check_industries(new: list[dict], existing: list[dict] | None = None) -> None:
    """Every industry must be selectable. Pairs the customer already has are left alone
    (a renamed/removed entry must not block saving an old record)."""
    existing = existing or []
    old_pairs = {(i["category"], i.get("subcategory")) for i in existing}
    old_cats = {i["category"] for i in existing}
    for ind in new:
        cat, sub = ind["category"], ind.get("subcategory")
        if (cat, sub) in old_pairs:
            continue
        _check_category(cat, sub, keep_category=cat if cat in old_cats else None)


def _sync_primary_industry(customer: Customer) -> None:
    first = (customer.industries or [None])[0]
    customer.category = first["category"] if first else None
    customer.subcategory = first.get("subcategory") if first else None


def _split(payload) -> tuple[dict, dict, list[str] | None]:
    """(scalar fields as python values, JSON fields in JSON mode, activity types)."""
    exclude = {"finalize", "category", "subcategory", *_JSON_FIELDS}  # category/subcategory: see industries
    scalars = payload.model_dump(exclude_unset=True, exclude=exclude)
    json_part = payload.model_dump(mode="json", exclude_unset=True, include=set(_JSON_FIELDS))
    activity = scalars.pop("activity_types", None)
    if activity is not None:
        activity = [a.value if hasattr(a, "value") else a for a in activity]
    return scalars, json_part, activity


def _apply(customer: Customer, scalars: dict, json_part: dict, activity: list[str] | None) -> None:
    for field, value in scalars.items():
        setattr(customer, field, value)
    for field, value in json_part.items():
        if field == "current_suppliers":
            value = _resolve_current_suppliers(value)
        setattr(customer, field, value)
    if activity is not None:
        customer.activity_types_csv = ",".join(dict.fromkeys(activity))  # de-duplicated, order kept
    if "industries" in json_part:
        _sync_primary_industry(customer)
    if "contact_log" in json_part:
        _derive_contact_log(customer)
    if "produced_products" in json_part:
        _derive_capacity(customer)


# ---------------------------------------------------------------------
# Create / update / finalize / delete
# ---------------------------------------------------------------------
def create_customer(actor: User, payload: CustomerCreate, *, ip_address: str | None) -> Customer:
    _require(actor, "create")
    _check_industries([i.model_dump() for i in payload.industries])
    _resolve_assignee(payload.assigned_to_user_id)

    scalars, json_part, activity = _split(payload)
    scalars.pop("registration_date", None)  # always the day of registration; clients can't set it
    customer = Customer(created_by_user_id=actor.id)
    _apply(customer, scalars, json_part, activity)
    # fields the schema defaults but exclude_unset would skip
    for field in _JSON_FIELDS:
        if getattr(customer, field) is None:
            setattr(customer, field, [])
    customer.registration_date = dt.date.today()
    if payload.customer_type == CustomerType.LEGAL:
        for f in _INDIVIDUAL_ONLY:
            setattr(customer, f, None)
    else:
        for f in _LEGAL_ONLY:
            setattr(customer, f, None)
    _derive_contact_log(customer)
    _derive_capacity(customer)
    _check_merged(customer)

    if payload.finalize:  # saved & submitted in one go
        customer.is_finalized = True
        customer.finalized_at = datetime.now(timezone.utc)
        customer.finalized_by_user_id = actor.id

    db.session.add(customer)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE, entity_id=customer.id,
        metadata={"display_name": customer.display_name, "finalized": customer.is_finalized}, ip_address=ip_address,
    )
    if customer.is_finalized:  # saved & submitted in one go: tell the managers a request is waiting
        for uid in request_ops.reviewer_ids("crm.customer.review", exclude=actor.id):
            notifications.notify(
                uid, "REVIEW_REQUEST", "درخواست جدید در انتظار بررسی",
                f"{actor.full_name} «{customer.display_name}» را برای بررسی ثبت کرد.", link=_link(customer),
            )
    db.session.commit()
    return customer


def update_customer(actor: User, customer_id: int, payload: CustomerUpdate, *, ip_address: str | None) -> Customer:
    customer = _get_or_404(customer_id)
    if not _can(actor, "update") and not request_ops.creator_may_edit(customer, actor.id):
        # not a manager, and not the creator inside the editable part of the workflow
        _require(actor, "update")
    changes = payload.model_dump(exclude_unset=True)

    existing_industries = _industries_of(customer)
    if "industries" not in changes and ("category" in changes or "subcategory" in changes):
        # Older single-industry clients: replace the FIRST industry, keep the others.
        new_cat = changes.get("category", customer.category)
        new_sub = changes.get("subcategory", customer.subcategory)
        if "category" in changes and new_cat != customer.category and "subcategory" not in changes:
            new_sub = None  # moving to another industry drops the old sub-category
        if not new_cat:
            raise ConflictError("Pick an industry before choosing a sub-category.")
        payload.industries = _dedupe_industries(
            [Industry(category=new_cat, subcategory=new_sub), *(Industry(**i) for i in existing_industries[1:])]
        )
        changes["industries"] = [i.model_dump() for i in payload.industries]
    if "industries" in changes:
        _check_industries(changes["industries"], existing_industries)
    if "assigned_to_user_id" in changes:
        _resolve_assignee(changes["assigned_to_user_id"])

    old_commercial = customer.commercial_status
    old_operational = customer.operational_status
    old_type = customer.customer_type

    try:
        scalars, json_part, activity = _split(payload)
        scalars.pop("registration_date", None)  # fixed at creation; not editable afterwards
        _apply(customer, scalars, json_part, activity)

        # identity must still be complete for the (possibly new) type
        try:
            check_identity(customer.customer_type, customer)
        except ValueError as e:
            raise ConflictError(str(e)) from e
        if customer.customer_type != old_type:
            for f in (_INDIVIDUAL_ONLY if customer.customer_type == CustomerType.LEGAL else _LEGAL_ONLY):
                setattr(customer, f, None)
        _check_merged(customer)
    except ConflictError:
        # The row was already modified in memory; make sure nothing of it is flushed later.
        db.session.rollback()
        raise

    db.session.flush()
    meta: dict = {"changed_fields": list(changes.keys())}
    if customer.commercial_status != old_commercial:
        meta["commercial_status"] = {"from": old_commercial.value, "to": customer.commercial_status.value}
    if customer.operational_status != old_operational:
        meta["operational_status"] = {"from": old_operational.value, "to": customer.operational_status.value}
    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE, entity_id=customer.id,
        metadata=meta, ip_address=ip_address,
    )
    db.session.commit()
    return customer


def finalize_customer(actor: User, customer_id: int, *, ip_address: str | None) -> Customer:
    """ثبت نهایی / ثبت مجدد -- the creator (or a manager) submits the file. Idempotent: submitting a
    file that is already in the review queue changes nothing."""
    customer = _get_or_404(customer_id)
    if customer.is_finalized and customer.review_status != "NEEDS_EDIT":
        if not (customer.created_by_user_id == actor.id or _can(actor, "update")):
            _require(actor, "update")
        return customer
    kind = request_ops.finalize(
        customer, actor, can_update=_can(actor, "update"), link=_link(customer), review_key="crm.customer.review"
    )
    write_audit_log(
        user_id=actor.id, action=kind, module=MODULE, entity_type=ENTITY_TYPE, entity_id=customer.id,
        ip_address=ip_address,
    )
    db.session.commit()
    return customer


def request_customer_change(actor: User, customer_id: int, reason: str, *, ip_address: str | None) -> Customer:
    customer = _get_or_404(customer_id)
    request_ops.request_change(customer, actor, reason, link=_link(customer), review_key="crm.customer.review")
    write_audit_log(user_id=actor.id, action="change_request", module=MODULE, entity_type=ENTITY_TYPE,
                    entity_id=customer.id, ip_address=ip_address)
    db.session.commit()
    return customer


def review_customer(actor: User, customer_id: int, action: str, note: str | None, *, ip_address: str | None) -> Customer:
    _require(actor, "review")
    customer = _get_or_404(customer_id)
    previous, new = request_ops.review(customer, actor, action, note, link=_link(customer))
    write_audit_log(user_id=actor.id, action=f"review_{action.lower()}", module=MODULE, entity_type=ENTITY_TYPE,
                    entity_id=customer.id, metadata={"from": previous, "to": new}, ip_address=ip_address)
    db.session.commit()
    return customer


def delete_customer(actor: User, customer_id: int, *, ip_address: str | None) -> None:
    _require(actor, "delete")
    customer = _get_or_404(customer_id)
    customer.deleted_at = datetime.now(timezone.utc)
    customer.is_active = False
    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE, entity_id=customer.id,
        ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Industry categories ("صنعت فعالیت"): main + sub, admin-managed
# ---------------------------------------------------------------------
def list_categories(actor: User) -> list[str]:
    """Main-category names for the list filter: every managed main category plus any
    name still used by a customer (e.g. one an admin later removed)."""
    _require(actor, "read")
    managed = [
        c.name for c in db.session.query(CustomerCategory)
        .filter(CustomerCategory.parent_id.is_(None))
        .order_by(CustomerCategory.sort_order, CustomerCategory.name)
    ]
    used = {
        i["category"]
        for row in db.session.query(Customer.industries, Customer.category, Customer.subcategory)
        .filter(Customer.deleted_at.is_(None)).all()
        for i in _rows_industries(*row)
        if i.get("category")
    }
    return managed + sorted(n for n in used if n not in managed)


def _rows_industries(industries, category, subcategory) -> list[dict]:
    if industries:
        return list(industries)
    return [{"category": category, "subcategory": subcategory}] if category else []


def _rename_in_industries(old_name: str, parent_name: str | None, new_name: str) -> None:
    """Rewrite a renamed main category (`parent_name is None`) or sub-category in every
    customer's industries, and re-mirror the first one into category/subcategory."""
    for cust in db.session.query(Customer).all():
        rows = _rows_industries(cust.industries, cust.category, cust.subcategory)
        changed = False
        out = []
        for ind in rows:
            ind = dict(ind)
            if parent_name is None and ind.get("category") == old_name:
                ind["category"] = new_name
                changed = True
            elif parent_name is not None and ind.get("category") == parent_name and ind.get("subcategory") == old_name:
                ind["subcategory"] = new_name
                changed = True
            out.append(ind)
        if changed:
            cust.industries = out
            _sync_primary_industry(cust)


def _customer_counts() -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    by_cat: dict[str, int] = {}
    by_sub: dict[tuple[str, str], int] = {}
    rows = db.session.query(Customer.industries, Customer.category, Customer.subcategory).filter(
        Customer.deleted_at.is_(None)
    ).all()
    for row in rows:
        cats: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        for i in _rows_industries(*row):  # a customer counts once per category / sub-category
            if not i.get("category"):
                continue
            cats.add(i["category"])
            if i.get("subcategory"):
                pairs.add((i["category"], i["subcategory"]))
        for cat in cats:
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for pair in pairs:
            by_sub[pair] = by_sub.get(pair, 0) + 1
    return by_cat, by_sub


def _category_dict(c: CustomerCategory, parent_name: str | None, by_cat, by_sub) -> dict:
    count = by_sub.get((parent_name, c.name), 0) if c.parent_id else by_cat.get(c.name, 0)
    return {
        "id": c.id, "name": c.name, "parent_id": c.parent_id, "is_active": c.is_active,
        "sort_order": c.sort_order, "customer_count": count,
    }


def list_category_items(actor: User) -> list[dict]:
    """Flat list of main + sub categories (clients group them by `parent_id`)."""
    _require(actor, "read")
    by_cat, by_sub = _customer_counts()
    rows = db.session.query(CustomerCategory).order_by(CustomerCategory.sort_order, CustomerCategory.name).all()
    names = {c.id: c.name for c in rows}
    return [_category_dict(c, names.get(c.parent_id), by_cat, by_sub) for c in rows]


def _get_category_or_404(category_id: int) -> CustomerCategory:
    c = db.session.get(CustomerCategory, category_id)
    if c is None:
        raise NotFoundError(f"Category {category_id} was not found.")
    return c


def _name_taken(name: str, parent_id: int | None, *, exclude_id: int | None = None) -> bool:
    q = db.session.query(CustomerCategory.id).filter(CustomerCategory.name == name)
    q = q.filter(CustomerCategory.parent_id.is_(None) if parent_id is None else CustomerCategory.parent_id == parent_id)
    if exclude_id is not None:
        q = q.filter(CustomerCategory.id != exclude_id)
    return q.first() is not None


def create_category(actor: User, payload: CategoryIn, *, ip_address: str | None) -> dict:
    _require(actor, "update")
    parent = None
    if payload.parent_id is not None:
        parent = _get_category_or_404(payload.parent_id)
        if parent.parent_id is not None:
            raise ConflictError("Sub-categories can only be added under a main category.")
    if _name_taken(payload.name, payload.parent_id):
        where = f" under '{parent.name}'" if parent else ""
        raise ConflictError(f"Category '{payload.name}' already exists{where}.")
    sibling = CustomerCategory.parent_id.is_(None) if parent is None else CustomerCategory.parent_id == parent.id
    last = db.session.query(db.func.max(CustomerCategory.sort_order)).filter(sibling).scalar() or 0
    c = CustomerCategory(name=payload.name, parent_id=payload.parent_id, sort_order=last + 1)
    db.session.add(c)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="create_category", module=MODULE, entity_type="customer_category",
        entity_id=c.id, metadata={"name": c.name, "parent_id": c.parent_id}, ip_address=ip_address,
    )
    db.session.commit()
    return _category_dict(c, parent.name if parent else None, {}, {})


def update_category(actor: User, category_id: int, payload: CategoryUpdate, *, ip_address: str | None) -> dict:
    """Rename / hide / reorder. Renaming also rewrites the customers that store the
    name (`category` for a main category, `subcategory` for a sub-category)."""
    _require(actor, "update")
    c = _get_category_or_404(category_id)
    parent = db.session.get(CustomerCategory, c.parent_id) if c.parent_id else None
    data = payload.model_dump(exclude_unset=True)
    old_name = c.name
    new_name = data.get("name")
    if new_name and new_name != old_name:
        if _name_taken(new_name, c.parent_id, exclude_id=c.id):
            raise ConflictError(f"Category '{new_name}' already exists.")
        c.name = new_name
        _rename_in_industries(old_name, parent.name if parent else None, new_name)
    if data.get("is_active") is not None:
        c.is_active = data["is_active"]
    if data.get("sort_order") is not None:
        c.sort_order = data["sort_order"]
    write_audit_log(
        user_id=actor.id, action="update_category", module=MODULE, entity_type="customer_category",
        entity_id=c.id, metadata={"changed_fields": list(data.keys()), "old_name": old_name}, ip_address=ip_address,
    )
    db.session.commit()
    by_cat, by_sub = _customer_counts()
    return _category_dict(c, parent.name if parent else None, by_cat, by_sub)


def delete_category(actor: User, category_id: int, *, ip_address: str | None) -> None:
    """Removes the name (and a main category's sub-categories) from the selectable
    list; customers already using it keep their stored values."""
    _require(actor, "update")
    c = _get_category_or_404(category_id)
    name, parent_id = c.name, c.parent_id
    db.session.query(CustomerCategory).filter(CustomerCategory.parent_id == c.id).delete(synchronize_session=False)
    db.session.delete(c)
    write_audit_log(
        user_id=actor.id, action="delete_category", module=MODULE, entity_type="customer_category",
        entity_id=category_id, metadata={"name": name, "parent_id": parent_id}, ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Product / grade pick-lists ("نام محصول" / "نام گرید"), admin-managed like the industries
# ---------------------------------------------------------------------
def _option_dict(o: CustomerOptionItem) -> dict:
    return {"id": o.id, "kind": o.kind.value, "name": o.name, "is_active": o.is_active, "sort_order": o.sort_order}


def _get_option_or_404(option_id: int) -> CustomerOptionItem:
    o = db.session.get(CustomerOptionItem, option_id)
    if o is None:
        raise NotFoundError(f"Option {option_id} was not found.")
    return o


def _require_write_option(actor: User) -> None:
    """Whoever may create OR edit customers may extend the lists (the wizard adds entries inline)."""
    if not (has_permission(actor, "crm.customer.create", None, None) or has_permission(actor, "crm.customer.update", None, None)):
        raise PermissionDeniedError("permission_denied", "Missing permission 'crm.customer.create' or 'crm.customer.update'.")


def list_option_items(actor: User, kind: str = "") -> list[dict]:
    _require(actor, "read")
    q = db.session.query(CustomerOptionItem)
    if kind in {k.value for k in OptionKind}:
        q = q.filter(CustomerOptionItem.kind == kind)
    return [_option_dict(o) for o in q.order_by(CustomerOptionItem.kind, CustomerOptionItem.sort_order, CustomerOptionItem.name)]


def create_option_item(actor: User, payload: OptionItemIn, *, ip_address: str | None) -> dict:
    _require_write_option(actor)
    exists = db.session.query(CustomerOptionItem.id).filter(
        CustomerOptionItem.kind == payload.kind, CustomerOptionItem.name == payload.name
    ).first()
    if exists:
        raise ConflictError(f"'{payload.name}' already exists in this list.")
    last = db.session.query(db.func.max(CustomerOptionItem.sort_order)).filter(
        CustomerOptionItem.kind == payload.kind
    ).scalar() or 0
    o = CustomerOptionItem(kind=payload.kind, name=payload.name, sort_order=last + 1)
    db.session.add(o)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="create_option", module=MODULE, entity_type="customer_option_item",
        entity_id=o.id, metadata={"kind": o.kind.value, "name": o.name}, ip_address=ip_address,
    )
    db.session.commit()
    return _option_dict(o)


def _rename_option_in_customers(kind: OptionKind, old: str, new: str) -> None:
    """A renamed product / grade is rewritten in every customer that stores the old name."""
    for cust in db.session.query(Customer).all():
        changed = False
        produced, consumed, suppliers = (
            [dict(p) for p in cust.produced_products or []],
            [dict(p) for p in cust.consumed_products or []],
            [{**sp, "grades": [dict(g) for g in sp.get("grades") or []]} for sp in cust.current_suppliers or []],
        )
        if kind in (OptionKind.PRODUCT, OptionKind.PRODUCED, OptionKind.CONSUMED):
            # produced and consumed products are separate lists: a rename only touches its own side
            # (the legacy shared list touches both)
            targets = []
            if kind in (OptionKind.PRODUCT, OptionKind.PRODUCED):
                targets += produced
            if kind in (OptionKind.PRODUCT, OptionKind.CONSUMED):
                targets += consumed
            for p in targets:
                if p.get("name") == old:
                    p["name"], changed = new, True
            if kind in (OptionKind.PRODUCT, OptionKind.CONSUMED):
                for sp in suppliers:
                    for g in sp["grades"]:
                        if g.get("product") == old:
                            g["product"], changed = new, True
        else:
            for p in consumed:
                if p.get("grade_specs") == old:
                    p["grade_specs"], changed = new, True
            for sp in suppliers:
                for g in sp["grades"]:
                    if g.get("grade") == old:
                        g["grade"], changed = new, True
        if changed:
            cust.produced_products, cust.consumed_products, cust.current_suppliers = produced, consumed, suppliers


def update_option_item(actor: User, option_id: int, payload: OptionItemUpdate, *, ip_address: str | None) -> dict:
    _require(actor, "update")
    o = _get_option_or_404(option_id)
    data = payload.model_dump(exclude_unset=True)
    old_name = o.name
    new_name = data.get("name")
    if new_name and new_name != old_name:
        if db.session.query(CustomerOptionItem.id).filter(
            CustomerOptionItem.kind == o.kind, CustomerOptionItem.name == new_name, CustomerOptionItem.id != o.id
        ).first():
            raise ConflictError(f"'{new_name}' already exists in this list.")
        o.name = new_name
        _rename_option_in_customers(o.kind, old_name, new_name)
    if data.get("is_active") is not None:
        o.is_active = data["is_active"]
    if data.get("sort_order") is not None:
        o.sort_order = data["sort_order"]
    write_audit_log(
        user_id=actor.id, action="update_option", module=MODULE, entity_type="customer_option_item",
        entity_id=o.id, metadata={"changed_fields": list(data.keys()), "old_name": old_name}, ip_address=ip_address,
    )
    db.session.commit()
    return _option_dict(o)


def delete_option_item(actor: User, option_id: int, *, ip_address: str | None) -> None:
    """Removes the name from the selectable list; customers already using it keep their value."""
    _require(actor, "update")
    o = _get_option_or_404(option_id)
    if o.kind == OptionKind.GRADE:
        # CRM sales reference the grade list directly (crm_sales.product_id), so a grade that has
        # recorded sales cannot be removed -- deactivate it instead (it stays on old sales).
        from app.modules.crm.models import CrmSale  # local import: crm depends on customers, not vice versa

        if db.session.query(CrmSale.id).filter(CrmSale.product_id == o.id).first():
            raise ConflictError(
                f"'{o.name}' is used by recorded CRM sales and cannot be deleted; deactivate it instead."
            )
    meta = {"kind": o.kind.value, "name": o.name}
    db.session.delete(o)
    write_audit_log(
        user_id=actor.id, action="delete_option", module=MODULE, entity_type="customer_option_item",
        entity_id=option_id, metadata=meta, ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Static option lists (so the client never hard-codes the enum labels)
# ---------------------------------------------------------------------
_COMMERCIAL_LABELS = {
    "NO_ACTION": "بدون اقدام",
    "MARKETING_NEGOTIATION": "در حال مذاکره و بازاریابی",
    "SAMPLE_SENT": "ارسال نمونه",
    "AWAITING_SAMPLE_APPROVAL": "منتظر تایید نمونه",
    "SALES_NEGOTIATION": "در حال مذاکره فروش",
    "ACQUIRED": "مشتری جذب شده",
    "REPEAT_ACTIVE": "مشتری تکرار شونده - فعال",
    "INACTIVE_LOST": "غیرفعال - از دست رفته",
    "POTENTIAL": "بالقوه",
}
_OPERATIONAL_LABELS = {"ACTIVE": "فعال", "INACTIVE": "غیرفعال"}
_ACTIVITY_LABELS = {"PRODUCER": "تولید کننده", "DISTRIBUTOR": "توزیع کننده", "EXPORTER": "صادر کننده"}
_PURCHASE_LABELS = {"OFFICIAL": "رسمی", "UNOFFICIAL": "غیر رسمی", "BOTH": "هر دو"}
_SOURCE_LABELS = {
    "WEBSITE": "وب‌سایت شرکت",
    "GOOGLE_SEARCH": "جست‌وجوی گوگل",
    "SOCIAL_MEDIA": "شبکه‌های اجتماعی",
    "EXHIBITION": "نمایشگاه و همایش",
    "CUSTOMER_REFERRAL": "معرفی مشتریان دیگر",
    "PARTNER_REFERRAL": "معرفی همکاران و ارتباطات تجاری",
    "INBOUND_CALL": "تماس ورودی مشتری",
    "OUTBOUND_CALL": "تماس خروجی شرکت",
    "FIELD_MARKETING": "بازاریابی حضوری",
    "TELEMARKETING": "بازاریابی تلفنی",
    "EMAIL_CAMPAIGN": "ایمیل تبلیغاتی",
    "MESSENGERS": "پیام‌رسان‌ها",
    "COMPANY_DATABASE": "بانک اطلاعاتی شرکت",
    "PREVIOUS_CONNECTIONS": "ارتباطات قبلی",
    "OTHER": "سایر",
}
_PAYMENT_LABELS = {"CASH": "نقدی", "CREDIT": "اعتباری", "CASH_CREDIT": "نقدی - اعتباری"}
# value -> (label, description)
_CREDIT_RATINGS = {
    "EXCELLENT": ("عالی", "پرداخت منظم و به‌موقع"),
    "GOOD": ("خوب", "تأخیرهای جزئی و محدود"),
    "AVERAGE": ("متوسط", "تأخیرهای تکرارشونده"),
    "WEAK": ("ضعیف", "تأخیرهای طولانی در پرداخت"),
    "BAD_DEBTOR": ("بدحساب", "بدهی معوق قابل‌توجه یا عدم پایبندی به تعهدات"),
    "NO_HISTORY": ("فاقد سابقه اعتباری", "هنوز معامله اعتباری نداشته است"),
    "NEEDS_REVIEW": ("نیازمند بررسی", "اطلاعات کافی برای ارزیابی وجود ندارد"),
}
_TYPE_LABELS = {"LEGAL": "حقوقی", "INDIVIDUAL": "حقیقی"}
_UNIT_LABELS = {"TON": "تن", "KG": "کیلوگرم"}
# سمت افراد تماس. The panel adds a final "سایر" choice with a free-text box, so any other
# position is stored as typed.
CONTACT_POSITIONS = [
    "مالک / مؤسس", "سهام‌دار", "مدیرعامل", "رئیس هیئت‌مدیره", "عضو هیئت‌مدیره", "مدیر مالی", "حسابدار",
    "مدیر بازرگانی", "مدیر فروش", "مدیر خرید و تدارکات", "کارشناس مالی", "کارشناس خرید", "کارشناس فروش",
    "نماینده قانونی", "صاحب امضای مجاز", "تصمیم‌گیرنده خرید", "تأییدکننده سفارش", "تأییدکننده پرداخت",
    "مشاور", "انباردار", "کمک‌انباردار", "کارشناس انبار",
]


def _options(labels: dict[str, str]) -> list[dict]:
    return [{"value": k, "label": v} for k, v in labels.items()]


def get_options(actor: User) -> dict:
    _require(actor, "read")
    return {
        "customer_types": _options(_TYPE_LABELS),
        "commercial_statuses": _options(_COMMERCIAL_LABELS),
        "operational_statuses": _options(_OPERATIONAL_LABELS),
        "activity_types": _options(_ACTIVITY_LABELS),
        "purchase_methods": _options(_PURCHASE_LABELS),
        "quantity_units": _options(_UNIT_LABELS),  # default TON
        "contact_positions": CONTACT_POSITIONS,
        "payment_types": _options(_PAYMENT_LABELS),
        "credit_months": list(range(1, 13)),  # plus a free-text "سایر" (credit_other)
        "acquaintance_sources": _options(_SOURCE_LABELS),
        "credit_ratings": [
            {"value": k, "label": f"{label} — {desc}", "description": desc} for k, (label, desc) in _CREDIT_RATINGS.items()
        ],
        # Step 5 only applies to customers in these stages ("مشتری جذب شده و در حال مذاکره فروش").
        "commercial_terms_statuses": ["SALES_NEGOTIATION", "ACQUIRED", "REPEAT_ACTIVE"],
    }