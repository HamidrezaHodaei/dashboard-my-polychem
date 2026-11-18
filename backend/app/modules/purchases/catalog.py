"""Purchase product catalog + remembered units.

The catalog is this module's own list (nothing shared with other modules). Reading/searching it needs
`procurement.purchase.read` (the wizard picks from it); creating / editing / deleting needs
`procurement.purchase.manage_catalog` (seeded for the admin role).

`code` is typed by the admin: free text kept as a String (letters of any script, digits and - _ . / \\ + # ( ) [ ] and
spaces). It is never generated, never converted to a number and may have leading zeros.
"""
import re

from sqlalchemy import func, select

from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.purchases import services as S
from app.modules.purchases.models import PurchaseItem, PurchaseProduct
from app.modules.purchases.schemas import ProductIn
from app.modules.suppliers.models import SupplierCategory
from app.utils.exceptions import ConflictError, InvalidInputError, NotFoundError

CODE_RE = re.compile(r"^[\w\-./\\+#()\[\] ]+$", re.UNICODE)


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"


def _clean_code(code: str | None) -> str | None:
    if code is None:
        return None
    code = code.strip()
    if not code:
        return None
    if not CODE_RE.match(code):
        raise InvalidInputError("کد کالا فقط می‌تواند شامل حروف، عدد و نشانه‌های - _ . / \\ + # ( ) [ ] باشد.", "code")
    return code


def _dict(p: PurchaseProduct, category_name: str | None, used: int | None = None) -> dict:
    out = {"id": p.id, "name": p.name, "code": p.code, "category_id": p.category_id,
           "category_name": category_name, "is_active": p.is_active}
    if used is not None:
        out["used_count"] = used
    return out


def _category_names() -> dict[int, str]:
    return dict(db.session.execute(select(SupplierCategory.id, SupplierCategory.name)).all())


def list_products(actor: User, *, q: str | None, category_id: int | None, page: int | None, per_page: int,
                  include_inactive: bool = False) -> tuple[list[dict], int]:
    S.require(actor, "read")
    admin = S.can(actor, "manage_catalog")
    stmt = select(PurchaseProduct)
    if not (include_inactive and admin):
        stmt = stmt.where(PurchaseProduct.is_active.is_(True))
    if category_id is not None:
        stmt = stmt.where(PurchaseProduct.category_id == category_id)
    if q and q.strip():
        like = _like(q.strip()[:100])
        stmt = stmt.where(PurchaseProduct.name.like(like, escape="\\") | PurchaseProduct.code.like(like, escape="\\"))
    total = db.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(PurchaseProduct.name)
    stmt = stmt.offset(((page or 1) - 1) * per_page).limit(per_page)
    rows = db.session.scalars(stmt).all()
    cats = _category_names()
    used = {}
    if admin and rows:
        used = dict(db.session.execute(
            select(PurchaseItem.product_id, func.count()).where(PurchaseItem.product_id.in_([r.id for r in rows]))
            .group_by(PurchaseItem.product_id)).all())
    return [_dict(r, cats.get(r.category_id), used.get(r.id, 0) if admin else None) for r in rows], total


def _check_unique(name: str, code: str | None, exclude_id: int | None) -> None:
    q = select(PurchaseProduct.id).where(func.lower(PurchaseProduct.name) == name.lower())
    if exclude_id:
        q = q.where(PurchaseProduct.id != exclude_id)
    if db.session.scalar(q) is not None:
        raise InvalidInputError("کالایی با این نام قبلاً تعریف شده است.", "name")
    if code:
        q = select(PurchaseProduct.id).where(func.lower(PurchaseProduct.code) == code.lower())
        if exclude_id:
            q = q.where(PurchaseProduct.id != exclude_id)
        if db.session.scalar(q) is not None:
            raise InvalidInputError("این کد کالا برای کالای دیگری ثبت شده است.", "code")


def _category_ok(category_id: int | None) -> None:
    if category_id is not None and db.session.get(SupplierCategory, category_id) is None:
        raise InvalidInputError("گروه کالایی معتبر نیست.", "category_id")


def create_product(actor: User, body: ProductIn, ip: str | None = None) -> dict:
    S.require(actor, "manage_catalog")
    name = (body.name or "").strip()
    S._need(name, "نام کالا را وارد کنید.", "name")
    code = _clean_code(body.code)
    _category_ok(body.category_id)
    _check_unique(name, code, None)
    p = PurchaseProduct(name=name, code=code, category_id=body.category_id,
                        is_active=True if body.is_active is None else body.is_active, created_by_user_id=actor.id)
    db.session.add(p)
    db.session.flush()
    write_audit_log(user_id=actor.id, action="create", module=S.MODULE, entity_type="purchase_product", entity_id=p.id,
                    metadata={"name": name, "code": code}, ip_address=ip)
    db.session.commit()
    return _dict(p, _category_names().get(p.category_id), 0)


def update_product(actor: User, product_id: int, body: ProductIn, ip: str | None = None) -> dict:
    S.require(actor, "manage_catalog")
    p = db.session.get(PurchaseProduct, product_id)
    if p is None:
        raise NotFoundError("کالا پیدا نشد.")
    data = body.model_dump(exclude_unset=True)
    before = {"name": p.name, "code": p.code, "category_id": p.category_id, "is_active": p.is_active}
    name = (data["name"] or "").strip() if "name" in data else p.name
    S._need(name, "نام کالا را وارد کنید.", "name")
    code = _clean_code(data["code"]) if "code" in data else p.code
    if "category_id" in data:
        _category_ok(data["category_id"])
        p.category_id = data["category_id"]
    _check_unique(name, code, p.id)
    p.name, p.code = name, code
    if data.get("is_active") is not None:
        p.is_active = data["is_active"]
    write_audit_log(user_id=actor.id, action="update", module=S.MODULE, entity_type="purchase_product", entity_id=p.id,
                    metadata={"before": before, "after": {"name": p.name, "code": p.code, "category_id": p.category_id,
                                                           "is_active": p.is_active}}, ip_address=ip)
    db.session.commit()
    return _dict(p, _category_names().get(p.category_id))


def delete_product(actor: User, product_id: int, ip: str | None = None) -> None:
    S.require(actor, "manage_catalog")
    p = db.session.get(PurchaseProduct, product_id)
    if p is None:
        raise NotFoundError("کالا پیدا نشد.")
    if db.session.scalar(select(func.count()).select_from(PurchaseItem).where(PurchaseItem.product_id == p.id)):
        raise ConflictError("این کالا در درخواست‌های خرید استفاده شده است؛ به‌جای حذف، آن را غیرفعال کنید.")
    write_audit_log(user_id=actor.id, action="delete", module=S.MODULE, entity_type="purchase_product", entity_id=p.id,
                    metadata={"name": p.name, "code": p.code}, ip_address=ip)
    db.session.delete(p)
    db.session.commit()


def search_units(actor: User, q: str | None, limit: int = 30) -> list[str]:
    """Every unit ever typed on an item (most used first). Purely suggestions: a new unit is always allowed."""
    S.require(actor, "read")
    stmt = select(PurchaseItem.unit).where(PurchaseItem.unit != "")
    if q and q.strip():
        stmt = stmt.where(PurchaseItem.unit.like(_like(q.strip()[:40]), escape="\\"))
    stmt = stmt.group_by(PurchaseItem.unit).order_by(func.count().desc(), PurchaseItem.unit).limit(min(max(limit, 1), 100))
    return list(db.session.scalars(stmt))
