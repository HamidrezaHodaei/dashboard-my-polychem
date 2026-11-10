"""
GET/POST/PATCH/DELETE /api/suppliers -- Procurement module.

`/api/suppliers/public` is the one route with NO `@require_authenticated`
-- it is what the public supplier-registration page submits to. It is
rate-limited (not identity-gated) to blunt abuse of an endpoint anyone on
the internet can call.

Catalog/datasheet files: upload first (`POST /files`, or `/files/public`
from the public form) -- the response is a file reference
`{id, name, size}` -- then send that reference inside `catalog_files` /
`products[].datasheet` when saving the supplier. Downloads (`GET
/files/<id>`) are staff-only. See files.py for storage details.
"""
from flask import Blueprint, g, request, send_file

from app.core.auth.decorators import require_authenticated
from app.core.export_files import collect_pages, send_export
from app.modules import export_rows
from app.extensions import limiter
from app.modules.suppliers import files, services
from app.modules.suppliers.schemas import (
    CategoryIn, CategoryUpdate, ChangeRequestIn, ReviewIn, SupplierCreate, SupplierCreateAdmin, SupplierPublic,
    SupplierUpdate,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("suppliers", __name__, url_prefix="/api/suppliers")


def _dump(supplier) -> dict:
    data = SupplierPublic.model_validate(supplier).model_dump(mode="json")
    user = getattr(g, "current_user", None)
    if user is not None:  # not on the public form's response
        data["my_actions"] = services.viewer_flags(user, supplier)
    return data


@bp.post("/public")
@limiter.limit("20 per hour")
def submit_public():
    payload = SupplierCreate.model_validate(request.get_json(silent=True) or {})
    supplier = services.create_public(payload, ip_address=request.remote_addr)
    return success_response(data=_dump(supplier), status_code=201)


@bp.post("/files/public")
@limiter.limit("60 per hour")
def upload_file_public():
    """No auth -- the public registration form uploads catalogs/datasheets here."""
    row = files.save_upload(request.files.get("file"), uploaded_by_user_id=None)
    return success_response(data=files.file_ref(row), status_code=201)


@bp.post("/files")
@require_authenticated
def upload_file():
    services.require_file_write(g.current_user)
    row = files.save_upload(request.files.get("file"), uploaded_by_user_id=g.current_user.id)
    return success_response(data=files.file_ref(row), status_code=201)


@bp.get("/files/<file_id>")
@require_authenticated
def download_file(file_id: str):
    services.require_file_read(g.current_user)
    row = files.get_file_or_404(file_id)
    response = send_file(
        files.disk_path(row), as_attachment=True, download_name=row.original_name,
        mimetype=row.content_type or "application/octet-stream",
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.get("/categories/public")
def public_categories():
    """No auth: the public registration form's selectable categories."""
    return success_response(data=services.list_public_categories())


@bp.get("/categories/public-tree")
def public_category_tree():
    """No auth: main categories with their sub-categories, for the public form."""
    return success_response(data=services.list_public_category_tree())


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


def _list_kwargs() -> dict:
    args = request.args
    return dict(
        search=args.get("search", ""), category=args.get("category", ""),
        subcategory=args.get("subcategory", ""),
        status=args.get("status", ""), quality=args.get("quality", ""),
        supplier_type=args.get("supplier_type", ""),
        include_inactive=args.get("include_inactive", "").lower() == "true",
    )


@bp.get("")
@require_authenticated
def list_suppliers():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_suppliers(g.current_user, page=page, per_page=per_page, **_list_kwargs())
    return success_response(
        data=[_dump(item) for item in items], meta={"page": page, "per_page": per_page, "total": total}
    )


@bp.get("/export")
@require_authenticated
def export_suppliers():
    """Excel / Word of the suppliers matching the current filters (`procurement.supplier.export`)."""
    export_rows.require_export(g.current_user, "procurement.supplier.export")
    kwargs = _list_kwargs()
    items = collect_pages(lambda p, n: services.list_suppliers(g.current_user, page=p, per_page=n, **kwargs))
    title, headers, rows = export_rows.suppliers_table(items)
    return send_export(request.args.get("format", "xlsx"), title=title, filename="suppliers", headers=headers, rows=rows)


@bp.get("/categories")
@require_authenticated
def list_categories():
    return success_response(data=services.list_categories(g.current_user))


@bp.get("/<int:supplier_id>")
@require_authenticated
def get_supplier(supplier_id: int):
    return success_response(data=_dump(services.get_supplier(g.current_user, supplier_id)))


@bp.post("")
@require_authenticated
def create_supplier():
    payload = SupplierCreateAdmin.model_validate(request.get_json(silent=True) or {})
    supplier = services.create_admin(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(supplier), status_code=201)


@bp.patch("/<int:supplier_id>")
@require_authenticated
def update_supplier(supplier_id: int):
    payload = SupplierUpdate.model_validate(request.get_json(silent=True) or {})
    supplier = services.update_supplier(g.current_user, supplier_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(supplier))


@bp.post("/<int:supplier_id>/finalize")
@require_authenticated
def finalize_supplier(supplier_id: int):
    supplier = services.finalize_supplier(g.current_user, supplier_id, ip_address=request.remote_addr)
    return success_response(data=_dump(supplier))


@bp.post("/<int:supplier_id>/request-change")
@require_authenticated
def request_supplier_change(supplier_id: int):
    payload = ChangeRequestIn.model_validate(request.get_json(silent=True) or {})
    supplier = services.request_supplier_change(g.current_user, supplier_id, payload.reason, ip_address=request.remote_addr)
    return success_response(data=_dump(supplier))


@bp.post("/<int:supplier_id>/review")
@require_authenticated
def review_supplier(supplier_id: int):
    payload = ReviewIn.model_validate(request.get_json(silent=True) or {})
    supplier = services.review_supplier(
        g.current_user, supplier_id, payload.action, payload.note, ip_address=request.remote_addr
    )
    return success_response(data=_dump(supplier))


@bp.delete("/<int:supplier_id>")
@require_authenticated
def delete_supplier(supplier_id: int):
    services.delete_supplier(g.current_user, supplier_id, ip_address=request.remote_addr)
    return success_response(data={})