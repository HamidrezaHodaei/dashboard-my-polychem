"""
Service layer for /api/suppliers -- Procurement module.

Same pattern as every other Phase 4 module (see
app/core/departments/services.py's docstring): permission checks live
here, not in routes.py. Suppliers are a single, un-scoped business
resource (no department/team ownership concept anywhere in the public
form or this request) -- every check below is GLOBAL-only
(`procurement.supplier.<action>`, scope_type=None/scope_id=None), the
same pattern already used for Roles/Permissions.

`create_public()` is the one function with NO permission check at all,
by design: it backs the public, unauthenticated supplier-registration
page (routes.py's `/api/suppliers/public`, rate-limited there, not
gated by auth). Every other function requires the actor to be an
authenticated staff member holding the relevant `procurement.supplier.*`
grant.
"""
from datetime import datetime, timezone

from app.core import request_ops
from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.suppliers import files
from app.modules.suppliers.models import (
    Supplier, SupplierCategory, SupplierFile, SupplierQuality, SupplierStatus, SupplierType,
)
from app.modules.suppliers.schemas import (
    CategoryIn, CategoryUpdate, SupplierCreate, SupplierCreateAdmin, SupplierUpdate, phones_from_contacts,
)
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "procurement"
ENTITY_TYPE = "supplier"


def _require(actor: User, action: str) -> None:
    key = f"procurement.supplier.{action}"
    if not has_permission(actor, key, None, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _can(actor: User, action: str) -> bool:
    return has_permission(actor, f"procurement.supplier.{action}", None, None)


LINK = "/procurement/suppliers"


def _link(supplier) -> str:
    return f"{LINK}?open={supplier.id}"
# Staff-evaluation fields: only managers set them, never the creator editing their own request.
_MANAGER_ONLY_FIELDS = ("status", "quality", "reviewed_by_user_id")


def viewer_flags(actor: User, supplier: Supplier) -> dict:
    """What THIS user may do with the record (the UI shows buttons from this; the server re-checks)."""
    return request_ops.viewer_flags(supplier, actor.id, can_update=_can(actor, "update"), can_review=_can(actor, "review"))


def require_file_read(actor: User) -> None:
    _require(actor, "read")


def require_file_write(actor: User) -> None:
    """Uploading is part of adding or editing a supplier."""
    # a creator saving their own (draft / returned) request uploads files too -- no `update` needed
    if _can(actor, "create") or _can(actor, "update"):
        return
    _require(actor, "create")


def _get_or_404(supplier_id: int) -> Supplier:
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None or supplier.deleted_at is not None:
        raise NotFoundError(f"Supplier {supplier_id} was not found.")
    return supplier


def _resolve_ref(ref):
    """A file reference must point at a real upload. The name/size stored on
    the supplier always come from the upload record, not from the client.
    Bare strings (older records) pass through unchanged."""
    if not isinstance(ref, dict):
        return ref
    row = db.session.get(SupplierFile, ref["id"])
    if row is None:
        raise ConflictError("An attached file was not found. Please upload it again.")
    return {"id": row.id, "name": row.original_name, "size": row.size}


def _resolve_catalog(items: list) -> list:
    return [_resolve_ref(i) for i in items]


def _resolve_image(ref):
    """The product photo must be an uploaded *image* file."""
    if ref is None:
        return None
    resolved = _resolve_ref(ref)
    row = db.session.get(SupplierFile, resolved["id"])
    if not files.is_image(row):
        raise ConflictError("The product image must be a PNG, JPG or WEBP file.")
    return resolved


def _resolve_products(products: list[dict]) -> list[dict]:
    return [
        {**p, "datasheet": _resolve_ref(p.get("datasheet")), "image": _resolve_image(p.get("image"))}
        for p in products
    ]


def _normalize_identity(supplier: Supplier) -> None:
    """نام برند یا مغازه belongs to individual suppliers only: a legal
    supplier's name IS its company, so any brand name is dropped."""
    if supplier.supplier_type == SupplierType.LEGAL:
        supplier.brand_name = None


def _apply(supplier: Supplier, payload: SupplierUpdate) -> None:
    data = payload.model_dump(exclude_unset=True)
    phones = data.pop("phones", None)
    contacts = data.pop("contacts", None)
    products = data.pop("products", None)
    catalog = data.pop("catalog_files", None)
    for field, value in data.items():
        setattr(supplier, field, value)
    if contacts is not None:
        supplier.contacts = contacts
        supplier.phones = phones_from_contacts(contacts)  # keep flat list in step
    elif phones is not None:
        supplier.phones = phones
    if products is not None:
        supplier.products = _resolve_products(products)
    if catalog is not None:
        supplier.catalog_files = _resolve_catalog(catalog)
    _normalize_identity(supplier)  # checks the merged row (a PATCH may only carry part of it)


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _product_match(term: str):
    """SQL condition: some product of the supplier matches `term` by name or
    specs. `products` is a JSON column, so MySQL uses JSON_SEARCH on exactly
    those two keys (a plain text scan would also match key names such as
    "name"); other dialects (the SQLite test DB) fall back to a text scan."""
    escaped = _escape_like(term)
    if db.engine.dialect.name == "mysql":
        return db.func.json_search(
            Supplier.products, "one", f"%{escaped}%", None, "$[*].name", "$[*].specs"
        ).isnot(None)
    return db.func.lower(db.cast(Supplier.products, db.Text)).like(f"%{escaped.lower()}%", escape="\\")


_AR_TO_FA = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_FA_TO_AR = str.maketrans({"ی": "ي", "ک": "ك"})
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _search_condition(term: str):
    """Free-text match over name / email / ids / postal code / products.

    Persian text is stored with either the Persian (ی ک) or the Arabic (ي ك)
    letter forms depending on the keyboard that typed it, so every text column
    is matched against both spellings; digits are matched in Latin form.
    """
    persian = term.translate(_AR_TO_FA)
    variants = {term, persian, persian.translate(_FA_TO_AR)}
    latin = term.translate(_DIGITS)

    conditions = [
        Supplier.national_id.like(f"%{latin}%"),
        Supplier.company_national_id.like(f"%{latin}%"),
        Supplier.postal_code.like(f"%{latin}%"),
    ]
    for variant in variants:
        like = f"%{variant.lower()}%"
        conditions += [
            db.func.lower(Supplier.company_name).like(like),
            db.func.lower(Supplier.first_name).like(like),
            db.func.lower(Supplier.last_name).like(like),
            db.func.lower(Supplier.brand_name).like(like),
            db.func.lower(Supplier.email).like(like),
            _product_match(variant),
        ]
    return db.or_(*conditions)


def list_suppliers(
    actor: User, *, page: int, per_page: int, search: str = "", category: str = "", subcategory: str = "",
    status: str = "", quality: str = "", supplier_type: str = "", include_inactive: bool = False,
):
    _require(actor, "read")

    query = db.session.query(Supplier).filter(Supplier.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(Supplier.is_active.is_(True))
    if category:
        query = query.filter(Supplier.category == category)
    if subcategory:
        query = query.filter(Supplier.subcategory == subcategory)
    if status:
        query = query.filter(Supplier.status == status)
    if quality:
        query = query.filter(Supplier.quality == quality)
    if supplier_type:
        query = query.filter(Supplier.supplier_type == supplier_type)
    if search:
        term = search.strip()
        if term:
            query = query.filter(_search_condition(term))

    query = query.order_by(Supplier.id.desc())
    return paginate_query(query, page, per_page)


def list_categories(actor: User) -> list[str]:
    """Main-category names for the panel's filter dropdown: every managed main
    category plus any name still used by a supplier row (e.g. one an admin
    later removed), so no supplier becomes un-filterable."""
    _require(actor, "read")
    managed = [
        c.name for c in db.session.query(SupplierCategory)
        .filter(SupplierCategory.parent_id.is_(None))
        .order_by(SupplierCategory.sort_order, SupplierCategory.name)
    ]
    used = [
        r[0] for r in db.session.query(Supplier.category)
        .filter(Supplier.deleted_at.is_(None), Supplier.category.isnot(None), Supplier.category != "")
        .distinct().all()
    ]
    return managed + sorted(n for n in used if n not in managed)


# ---------------------------------------------------------------------
# Category management (admin panel) + the public form's selectable list
# ---------------------------------------------------------------------
def list_public_categories() -> list[str]:
    """No auth -- main categories for the public registration form's select
    (kept as a plain list of names for the existing form)."""
    rows = (
        db.session.query(SupplierCategory.name)
        .filter(SupplierCategory.is_active.is_(True), SupplierCategory.parent_id.is_(None))
        .order_by(SupplierCategory.sort_order, SupplierCategory.name)
        .all()
    )
    return [r[0] for r in rows]


def list_public_category_tree() -> list[dict]:
    """No auth -- [{name, subcategories: [name, ...]}] of active entries; a
    sub-category is only offered while its main category is active too."""
    rows = (
        db.session.query(SupplierCategory)
        .filter(SupplierCategory.is_active.is_(True))
        .order_by(SupplierCategory.sort_order, SupplierCategory.name)
        .all()
    )
    subs: dict[int, list[str]] = {}
    for c in rows:
        if c.parent_id is not None:
            subs.setdefault(c.parent_id, []).append(c.name)
    return [
        {"name": c.name, "subcategories": subs.get(c.id, [])}
        for c in rows if c.parent_id is None
    ]


def _supplier_counts() -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    """(per main-category count, per (category, subcategory) count)."""
    by_cat: dict[str, int] = {}
    by_sub: dict[tuple[str, str], int] = {}
    rows = (
        db.session.query(Supplier.category, Supplier.subcategory, db.func.count(Supplier.id))
        .filter(Supplier.deleted_at.is_(None), Supplier.category.isnot(None))
        .group_by(Supplier.category, Supplier.subcategory).all()
    )
    for cat, sub, n in rows:
        by_cat[cat] = by_cat.get(cat, 0) + n
        if sub:
            by_sub[(cat, sub)] = n
    return by_cat, by_sub


def _category_dict(c: SupplierCategory, parent_name: str | None, by_cat, by_sub) -> dict:
    count = by_sub.get((parent_name, c.name), 0) if c.parent_id else by_cat.get(c.name, 0)
    return {
        "id": c.id, "name": c.name, "parent_id": c.parent_id, "is_active": c.is_active,
        "sort_order": c.sort_order, "supplier_count": count,
    }


def list_category_items(actor: User) -> list[dict]:
    """Flat list of main + sub categories (clients group them by `parent_id`)."""
    _require(actor, "read")
    by_cat, by_sub = _supplier_counts()
    rows = db.session.query(SupplierCategory).order_by(SupplierCategory.sort_order, SupplierCategory.name).all()
    names = {c.id: c.name for c in rows}
    return [_category_dict(c, names.get(c.parent_id), by_cat, by_sub) for c in rows]


def _get_category_or_404(category_id: int) -> SupplierCategory:
    c = db.session.get(SupplierCategory, category_id)
    if c is None:
        raise NotFoundError(f"Category {category_id} was not found.")
    return c


def _name_taken(name: str, parent_id: int | None, *, exclude_id: int | None = None) -> bool:
    q = db.session.query(SupplierCategory.id).filter(SupplierCategory.name == name)
    q = q.filter(SupplierCategory.parent_id.is_(None) if parent_id is None else SupplierCategory.parent_id == parent_id)
    if exclude_id is not None:
        q = q.filter(SupplierCategory.id != exclude_id)
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
    sibling = SupplierCategory.parent_id.is_(None) if parent is None else SupplierCategory.parent_id == parent.id
    last = db.session.query(db.func.max(SupplierCategory.sort_order)).filter(sibling).scalar() or 0
    c = SupplierCategory(name=payload.name, parent_id=payload.parent_id, sort_order=last + 1)
    db.session.add(c)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="create_category", module=MODULE, entity_type="supplier_category",
        entity_id=c.id, metadata={"name": c.name, "parent_id": c.parent_id}, ip_address=ip_address,
    )
    db.session.commit()
    return _category_dict(c, parent.name if parent else None, {}, {})


def update_category(actor: User, category_id: int, payload: CategoryUpdate, *, ip_address: str | None) -> dict:
    """Rename / hide / reorder. Renaming also rewrites the supplier rows that
    store the name (`category` for a main category, `subcategory` for a
    sub-category) so existing suppliers follow the new name."""
    _require(actor, "update")
    c = _get_category_or_404(category_id)
    parent = db.session.get(SupplierCategory, c.parent_id) if c.parent_id else None
    data = payload.model_dump(exclude_unset=True)
    old_name = c.name
    new_name = data.get("name")
    if new_name and new_name != old_name:
        if _name_taken(new_name, c.parent_id, exclude_id=c.id):
            raise ConflictError(f"Category '{new_name}' already exists.")
        c.name = new_name
        if parent is None:
            db.session.query(Supplier).filter(Supplier.category == old_name).update(
                {Supplier.category: new_name}, synchronize_session=False
            )
        else:
            db.session.query(Supplier).filter(
                Supplier.category == parent.name, Supplier.subcategory == old_name
            ).update({Supplier.subcategory: new_name}, synchronize_session=False)
    if "is_active" in data and data["is_active"] is not None:
        c.is_active = data["is_active"]
    if "sort_order" in data and data["sort_order"] is not None:
        c.sort_order = data["sort_order"]
    write_audit_log(
        user_id=actor.id, action="update_category", module=MODULE, entity_type="supplier_category",
        entity_id=c.id, metadata={"changed_fields": list(data.keys()), "old_name": old_name}, ip_address=ip_address,
    )
    db.session.commit()
    by_cat, by_sub = _supplier_counts()
    return _category_dict(c, parent.name if parent else None, by_cat, by_sub)


def delete_category(actor: User, category_id: int, *, ip_address: str | None) -> None:
    """Removes the name (and, for a main category, its sub-categories) from the
    selectable list. Suppliers that already use it keep their stored values
    (they just stop being offered to new submissions)."""
    _require(actor, "update")
    c = _get_category_or_404(category_id)
    name = c.name
    # Explicit (not only the DB's ON DELETE CASCADE) so it also holds where
    # foreign keys aren't enforced, e.g. SQLite.
    db.session.query(SupplierCategory).filter(SupplierCategory.parent_id == c.id).delete(synchronize_session=False)
    db.session.delete(c)
    write_audit_log(
        user_id=actor.id, action="delete_category", module=MODULE, entity_type="supplier_category",
        entity_id=category_id, metadata={"name": name, "parent_id": c.parent_id}, ip_address=ip_address,
    )
    db.session.commit()


def _check_category(
    category: str | None, subcategory: str | None = None, *,
    keep_category: str | None = None, keep_subcategory: str | None = None,
) -> None:
    """A submitted category must be one of the active, admin-managed names, and
    a sub-category must be an active child of that category. The `keep_*`
    values let an edit save a supplier whose existing (legacy/removed)
    values are unchanged."""
    if subcategory and not category:
        raise ConflictError("Pick a category before choosing a sub-category.")
    parent = None
    if category and category != keep_category:
        parent = db.session.query(SupplierCategory).filter(
            SupplierCategory.name == category, SupplierCategory.parent_id.is_(None),
            SupplierCategory.is_active.is_(True),
        ).first()
        if parent is None:
            raise ConflictError(f"Category '{category}' is not available. Please pick one from the list.")
    if subcategory and not (subcategory == keep_subcategory and category == keep_category):
        if parent is None:
            parent = db.session.query(SupplierCategory).filter(
                SupplierCategory.name == category, SupplierCategory.parent_id.is_(None)
            ).first()
        ok = parent is not None and db.session.query(SupplierCategory.id).filter(
            SupplierCategory.parent_id == parent.id, SupplierCategory.name == subcategory,
            SupplierCategory.is_active.is_(True),
        ).first()
        if not ok:
            raise ConflictError(f"Sub-category '{subcategory}' is not available under '{category}'.")


def get_supplier(actor: User, supplier_id: int) -> Supplier:
    _require(actor, "read")
    return _get_or_404(supplier_id)


def create_public(payload: SupplierCreate, *, ip_address: str | None) -> Supplier:
    """No permission check -- this is the public submission endpoint."""
    _check_category(payload.category, payload.subcategory)
    supplier = Supplier(
        is_public_submission=True,
        status=SupplierStatus.SEMI_ACTIVE,
        **payload.model_dump(exclude={"phones", "contacts", "products", "catalog_files"}),
        phones=[p.model_dump() for p in payload.phones],
        contacts=[c.model_dump() for c in payload.contacts],
        products=_resolve_products([p.model_dump() for p in payload.products]),
        catalog_files=_resolve_catalog(payload.model_dump()["catalog_files"]),
    )
    _normalize_identity(supplier)
    db.session.add(supplier)
    db.session.flush()
    write_audit_log(
        user_id=None, action="create", module=MODULE, entity_type=ENTITY_TYPE, entity_id=supplier.id,
        metadata={"source": "public_form", "display_name": supplier.display_name}, ip_address=ip_address,
    )
    db.session.commit()
    return supplier


def create_admin(actor: User, payload: SupplierCreateAdmin, *, ip_address: str | None) -> Supplier:
    _require(actor, "create")
    _check_category(payload.category, payload.subcategory)
    supplier = Supplier(
        is_public_submission=False,
        created_by_user_id=actor.id,
        finalized_at=datetime.now(timezone.utc) if payload.is_finalized else None,
        **payload.model_dump(exclude={"phones", "contacts", "products", "catalog_files"}),
        phones=[p.model_dump() for p in payload.phones],
        contacts=[c.model_dump() for c in payload.contacts],
        products=_resolve_products([p.model_dump() for p in payload.products]),
        catalog_files=_resolve_catalog(payload.model_dump()["catalog_files"]),
    )
    _normalize_identity(supplier)
    db.session.add(supplier)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE, entity_id=supplier.id,
        metadata={"source": "admin", "display_name": supplier.display_name}, ip_address=ip_address,
    )
    db.session.commit()
    return supplier


def update_supplier(actor: User, supplier_id: int, payload: SupplierUpdate, *, ip_address: str | None) -> Supplier:
    supplier = _get_or_404(supplier_id)
    as_manager = _can(actor, "update")
    if not as_manager and not request_ops.creator_may_edit(supplier, actor.id):
        # not a manager, and not the creator inside the editable part of the workflow
        _require(actor, "update")
    changes = payload.model_dump(exclude_unset=True)
    if not as_manager:
        for field in _MANAGER_ONLY_FIELDS:
            if field in changes:
                changes.pop(field)
                setattr(payload, field, None)
                payload.model_fields_set.discard(field)
    if "category" in changes or "subcategory" in changes:
        new_cat = changes.get("category", supplier.category)
        if "category" in changes and new_cat != supplier.category and "subcategory" not in changes:
            # Moving to another main category drops the old sub-category.
            payload.subcategory = None
            changes["subcategory"] = None
        _check_category(
            new_cat, changes.get("subcategory", supplier.subcategory),
            keep_category=supplier.category, keep_subcategory=supplier.subcategory,
        )

    _apply(supplier, payload)
    if "reviewed_by_user_id" not in changes and ("status" in changes or "quality" in changes):
        supplier.reviewed_by_user_id = actor.id

    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE, entity_id=supplier.id,
        metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return supplier


def finalize_supplier(actor: User, supplier_id: int, *, ip_address: str | None) -> Supplier:
    """ثبت نهایی / ثبت مجدد -- the creator submits the draft, or re-submits after corrections."""
    supplier = _get_or_404(supplier_id)
    kind = request_ops.finalize(
        supplier, actor, can_update=_can(actor, "update"), link=_link(supplier), review_key="procurement.supplier.review"
    )
    write_audit_log(user_id=actor.id, action=kind, module=MODULE, entity_type=ENTITY_TYPE, entity_id=supplier.id,
                    ip_address=ip_address)
    db.session.commit()
    return supplier


def request_supplier_change(actor: User, supplier_id: int, reason: str, *, ip_address: str | None) -> Supplier:
    supplier = _get_or_404(supplier_id)
    request_ops.request_change(supplier, actor, reason, link=_link(supplier), review_key="procurement.supplier.review")
    write_audit_log(user_id=actor.id, action="change_request", module=MODULE, entity_type=ENTITY_TYPE,
                    entity_id=supplier.id, ip_address=ip_address)
    db.session.commit()
    return supplier


def review_supplier(actor: User, supplier_id: int, action: str, note: str | None, *, ip_address: str | None) -> Supplier:
    _require(actor, "review")
    supplier = _get_or_404(supplier_id)
    previous, new = request_ops.review(supplier, actor, action, note, link=_link(supplier))
    write_audit_log(user_id=actor.id, action=f"review_{action.lower()}", module=MODULE, entity_type=ENTITY_TYPE,
                    entity_id=supplier.id, metadata={"from": previous, "to": new}, ip_address=ip_address)
    db.session.commit()
    return supplier


def delete_supplier(actor: User, supplier_id: int, *, ip_address: str | None) -> None:
    _require(actor, "delete")
    supplier = _get_or_404(supplier_id)
    supplier.deleted_at = datetime.now(timezone.utc)
    supplier.is_active = False
    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE, entity_id=supplier.id,
        ip_address=ip_address,
    )
    db.session.commit()