"""
/api/crm -- CRM sales module. Every route requires authentication; permissions
(`crm.sale.*`; `crm.product.*` now guards the payment-method catalogue) are enforced in services.py.

Static paths are declared before `/<int:id>`. All list/analytics endpoints share ONE filter
parser (services.parse_filters), so the table, the KPI cards and every chart always describe the
same set of sales.
"""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.export_files import collect_pages, send_export
from app.modules import export_rows
from app.modules.crm import services
from app.modules.crm.schemas import (
    ImportRequest, PaymentMethodIn, PaymentMethodUpdate, SaleCreate, SaleUpdate,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("crm", __name__, url_prefix="/api/crm")


def _json():
    return request.get_json(silent=True) or {}


def _flag(name: str) -> bool:
    return (request.args.get(name) or "").strip().lower() in ("1", "true", "yes")


# ── filters / pickers / analytics ────────────────────────────────────
@bp.get("/options")
@require_authenticated
def options():
    return success_response(data=services.sales_filter_options(g.current_user))


@bp.get("/customers")
@require_authenticated
def customer_picker():
    limit = request.args.get("limit", 20, type=int)
    return success_response(
        data=services.lookup_customers(
            g.current_user, search=request.args.get("search", ""), limit=limit,
            customer_id=request.args.get("id", type=int),
        )
    )


@bp.get("/analytics")
@require_authenticated
def analytics():
    filters = services.parse_filters(request.args)
    top = max(3, min(request.args.get("top", 8, type=int), 20))
    return success_response(data=services.analytics(g.current_user, filters, top=top))


# ── sales ────────────────────────────────────────────────────────────
@bp.get("/sales")
@require_authenticated
def list_sales():
    page, per_page = parse_pagination(request.args)
    filters = services.parse_filters(request.args)
    items, total = services.list_sales(
        g.current_user, page=page, per_page=per_page, filters=filters, sort=request.args.get("sort", "-date")
    )
    return success_response(
        data=[services.dump_sale(s) for s in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/sales/export")
@require_authenticated
def export_sales():
    """Excel (or Word) of the sales matching the current filters (`crm.sale.export`)."""
    export_rows.require_export(g.current_user, "crm.sale.export")
    filters = services.parse_filters(request.args)
    sort = request.args.get("sort", "-date")
    items = collect_pages(lambda p, n: services.list_sales(g.current_user, page=p, per_page=n, filters=filters, sort=sort))
    title, headers, rows = export_rows.sales_table([services.dump_sale(s) for s in items])
    return send_export(request.args.get("format", "xlsx"), title=title, filename="crm-sales", headers=headers, rows=rows)


@bp.post("/sales/import")
@require_authenticated
def import_sales():
    payload = ImportRequest.model_validate(_json())
    return success_response(data=services.import_sales(g.current_user, payload, ip_address=request.remote_addr))


@bp.get("/sales/<int:sale_id>")
@require_authenticated
def get_sale(sale_id: int):
    return success_response(data=services.dump_sale(services.get_sale(g.current_user, sale_id)))


@bp.post("/sales")
@require_authenticated
def create_sale():
    payload = SaleCreate.model_validate(_json())
    sale = services.create_sale(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=services.dump_sale(sale), status_code=201)


@bp.patch("/sales/<int:sale_id>")
@require_authenticated
def update_sale(sale_id: int):
    payload = SaleUpdate.model_validate(_json())
    sale = services.update_sale(g.current_user, sale_id, payload, ip_address=request.remote_addr)
    return success_response(data=services.dump_sale(sale))


@bp.delete("/sales/<int:sale_id>")
@require_authenticated
def delete_sale(sale_id: int):
    services.delete_sale(g.current_user, sale_id, ip_address=request.remote_addr)
    return success_response(data={})


# ── products (read-only: the list is the customer bank's product pick-list) ──
@bp.get("/products")
@require_authenticated
def list_products():
    return success_response(data=services.list_products(g.current_user, include_inactive=_flag("include_inactive")))


# ── payment methods ──────────────────────────────────────────────────
@bp.get("/payment-methods")
@require_authenticated
def list_payment_methods():
    return success_response(
        data=services.list_payment_methods(g.current_user, include_inactive=_flag("include_inactive"))
    )


@bp.post("/payment-methods")
@require_authenticated
def create_payment_method():
    payload = PaymentMethodIn.model_validate(_json())
    return success_response(
        data=services.create_payment_method(g.current_user, payload, ip_address=request.remote_addr), status_code=201
    )


@bp.patch("/payment-methods/<int:method_id>")
@require_authenticated
def update_payment_method(method_id: int):
    payload = PaymentMethodUpdate.model_validate(_json())
    return success_response(
        data=services.update_payment_method(g.current_user, method_id, payload, ip_address=request.remote_addr)
    )


@bp.delete("/payment-methods/<int:method_id>")
@require_authenticated
def delete_payment_method(method_id: int):
    services.delete_payment_method(
        g.current_user, method_id, force=_flag("force"), ip_address=request.remote_addr
    )
    return success_response(data={})
