"""
/api/customers -- CRM module (6-step customer file).

Every route requires authentication; permissions are `crm.customer.<read|create|
update|delete>` and are checked in services.py. Static paths (`/options`, `/stats`,
`/locations`, `/categories`, `/category-items`) are declared before `/<int:id>`.
"""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.export_files import collect_pages, send_export
from app.modules import export_rows
from app.modules.customers import services
from app.core.request_schemas import ChangeRequestIn, ReviewIn
from app.modules.customers.schemas import (
    CategoryIn, CategoryUpdate, CustomerCreate, CustomerPublic, CustomerUpdate, OptionItemIn, OptionItemUpdate,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("customers", __name__, url_prefix="/api/customers")


def _dump(customer) -> dict:
    data = CustomerPublic.model_validate(customer).model_dump(mode="json")
    data["my_actions"] = services.viewer_flags(g.current_user, customer)
    return data


def _flag(value: str) -> bool | None:
    value = (value or "").strip().lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    return None


@bp.get("/options")
@require_authenticated
def options():
    return success_response(data=services.get_options(g.current_user))


@bp.get("/stats")
@require_authenticated
def stats():
    return success_response(data=services.customer_stats(g.current_user))


@bp.get("/assignable-users")
@require_authenticated
def assignable_users():
    return success_response(data=services.list_assignable_users(g.current_user))


@bp.get("/locations")
@require_authenticated
def locations():
    return success_response(data=services.list_locations(g.current_user))


# ── industry categories (main + sub) ─────────────────────────────────
@bp.get("/categories")
@require_authenticated
def list_categories():
    return success_response(data=services.list_categories(g.current_user))


@bp.get("/category-items")
@require_authenticated
def list_category_items():
    return success_response(data=services.list_category_items(g.current_user))


@bp.post("/category-items")
@require_authenticated
def create_category():
    payload = CategoryIn.model_validate(request.get_json(silent=True) or {})
    return success_response(
        data=services.create_category(g.current_user, payload, ip_address=request.remote_addr), status_code=201
    )


@bp.patch("/category-items/<int:category_id>")
@require_authenticated
def update_category(category_id: int):
    payload = CategoryUpdate.model_validate(request.get_json(silent=True) or {})
    return success_response(
        data=services.update_category(g.current_user, category_id, payload, ip_address=request.remote_addr)
    )


@bp.delete("/category-items/<int:category_id>")
@require_authenticated
def delete_category(category_id: int):
    services.delete_category(g.current_user, category_id, ip_address=request.remote_addr)
    return success_response(data={})


# ── product / grade pick-lists ───────────────────────────────────────
@bp.get("/option-items")
@require_authenticated
def list_option_items():
    return success_response(data=services.list_option_items(g.current_user, request.args.get("kind", "")))


@bp.post("/option-items")
@require_authenticated
def create_option_item():
    payload = OptionItemIn.model_validate(request.get_json(silent=True) or {})
    return success_response(
        data=services.create_option_item(g.current_user, payload, ip_address=request.remote_addr), status_code=201
    )


@bp.patch("/option-items/<int:option_id>")
@require_authenticated
def update_option_item(option_id: int):
    payload = OptionItemUpdate.model_validate(request.get_json(silent=True) or {})
    return success_response(
        data=services.update_option_item(g.current_user, option_id, payload, ip_address=request.remote_addr)
    )


@bp.delete("/option-items/<int:option_id>")
@require_authenticated
def delete_option_item(option_id: int):
    services.delete_option_item(g.current_user, option_id, ip_address=request.remote_addr)
    return success_response(data={})


# ── customers ────────────────────────────────────────────────────────
def _list_kwargs() -> dict:
    """The filters of the list screen -- shared by the table and the Excel / Word export."""
    args = request.args
    statuses = [s.strip() for raw in args.getlist("commercial_status") for s in raw.split(",") if s.strip()]
    return dict(
        search=args.get("search", ""), category=args.get("category", ""), subcategory=args.get("subcategory", ""),
        commercial_statuses=statuses, operational_status=args.get("operational_status", ""),
        customer_type=args.get("customer_type", ""), province=args.get("province", ""), city=args.get("city", ""),
        activity_type=args.get("activity_type", ""), assigned_to=args.get("assigned_to", ""),
        credit_rating=args.get("credit_rating", ""),
        follow_up_due=_flag(args.get("follow_up_due", "")) is True,
        is_finalized=_flag(args.get("is_finalized", "")),
        include_inactive=_flag(args.get("include_inactive", "")) is True,
        sort=args.get("sort", "-created_at"), review_status=args.get("review_status", ""),
    )


@bp.get("")
@require_authenticated
def list_customers():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_customers(g.current_user, page=page, per_page=per_page, **_list_kwargs())
    return success_response(
        data=[_dump(item) for item in items], meta={"page": page, "per_page": per_page, "total": total}
    )


@bp.get("/export")
@require_authenticated
def export_customers():
    """Excel / Word of the customers matching the current filters (`crm.customer.export`)."""
    export_rows.require_export(g.current_user, "crm.customer.export")
    kwargs = _list_kwargs()
    items = collect_pages(lambda p, n: services.list_customers(g.current_user, page=p, per_page=n, **kwargs))
    title, headers, rows = export_rows.customers_table(items)
    return send_export(request.args.get("format", "xlsx"), title=title, filename="customers", headers=headers, rows=rows)


@bp.get("/<int:customer_id>")
@require_authenticated
def get_customer(customer_id: int):
    return success_response(data=_dump(services.get_customer(g.current_user, customer_id)))


@bp.post("")
@require_authenticated
def create_customer():
    payload = CustomerCreate.model_validate(request.get_json(silent=True) or {})
    customer = services.create_customer(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(customer), status_code=201)


@bp.patch("/<int:customer_id>")
@require_authenticated
def update_customer(customer_id: int):
    payload = CustomerUpdate.model_validate(request.get_json(silent=True) or {})
    customer = services.update_customer(g.current_user, customer_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(customer))


@bp.post("/<int:customer_id>/finalize")
@require_authenticated
def finalize_customer(customer_id: int):
    customer = services.finalize_customer(g.current_user, customer_id, ip_address=request.remote_addr)
    return success_response(data=_dump(customer))


@bp.post("/<int:customer_id>/request-change")
@require_authenticated
def request_customer_change(customer_id: int):
    payload = ChangeRequestIn.model_validate(request.get_json(silent=True) or {})
    customer = services.request_customer_change(g.current_user, customer_id, payload.reason, ip_address=request.remote_addr)
    return success_response(data=_dump(customer))


@bp.post("/<int:customer_id>/review")
@require_authenticated
def review_customer(customer_id: int):
    payload = ReviewIn.model_validate(request.get_json(silent=True) or {})
    customer = services.review_customer(
        g.current_user, customer_id, payload.action, payload.note, ip_address=request.remote_addr
    )
    return success_response(data=_dump(customer))


@bp.delete("/<int:customer_id>")
@require_authenticated
def delete_customer(customer_id: int):
    services.delete_customer(g.current_user, customer_id, ip_address=request.remote_addr)
    return success_response(data={})