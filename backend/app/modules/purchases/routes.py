"""
/api/purchases -- Purchase Reports (procurement). All routes need a logged-in staff member; what each
may do is decided in services.py / reports.py by `procurement.purchase.<action>`.

    GET    /meta                      lists for the wizard (commodity groups, labels, units, my permissions)
    GET    /suppliers?q=              supplier bank search for the quotation step
    POST   /files                     upload an attachment -> {id, name, size}
    GET    /files/<id>                download an attachment
    GET    /                          list (filters + server-side sort/pagination, ?kpi= for KPI details)
    POST   /                          create a draft (step 1 data may be partial)
    GET    /<id>
    PUT    /<id>/basic|items|budget|inquiries|selection|result      save a wizard step (`complete` true = validate it)
    POST   /<id>/submit               steps 1-3 done -> quotation stage (also resubmit after a revision)
    POST   /<id>/cancel               {note}
    POST   /<id>/send-back            {note}  (needs approve) -> needs revision / reopens a closed one
    POST   /<id>/approve-reference    {item_ids}  (needs approve)
    DELETE /<id>                      soft delete (drafts / cancelled only)
    GET    /dashboard                 KPIs, groups, trends, supplier performance
    GET    /export?kind=&format=      xlsx download, or format=json for the print / PDF view
"""
from io import BytesIO

from flask import Blueprint, g, request, send_file

from app.core.auth.decorators import require_authenticated
from app.core.export_files import XLSX_MIME, _safe
from app.modules.purchases import catalog, direct, files, reports, services
from app.modules.purchases.schemas import (
    ApproveReferenceIn, BasicIn, BudgetIn, DirectIn, InquiriesIn, ItemsIn, NoteIn, ProductIn, ResultIn, ReviewIn, SelectionIn,
)
from app.modules.purchases.serialize import request_dict
from app.utils.exceptions import InvalidInputError
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("purchases", __name__, url_prefix="/api/purchases")


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _ok(req, status_code: int = 200):
    return success_response(data=request_dict(req, g.current_user), status_code=status_code)


@bp.get("/meta")
@require_authenticated
def meta():
    return success_response(data=services.meta(g.current_user))


@bp.get("/suppliers")
@require_authenticated
def suppliers():
    return success_response(data=services.search_suppliers(g.current_user, request.args.get("q")))


@bp.get("/units")
@require_authenticated
def units():
    return success_response(data=catalog.search_units(g.current_user, request.args.get("q")))


@bp.get("/products")
@require_authenticated
def products():
    """Catalog search (wizard) or, with `page`, the admin's paginated list (`include_inactive=1` for admins)."""
    page = request.args.get("page", type=int)
    per_page = min(max(request.args.get("per_page", 20 if page else 30, type=int), 1), 100)
    cat = request.args.get("category_id", type=int)
    rows, total = catalog.list_products(g.current_user, q=request.args.get("q"), category_id=cat, page=page,
                                        per_page=per_page, include_inactive=request.args.get("include_inactive") == "1")
    return success_response(data=rows, meta={"page": page or 1, "per_page": per_page, "total": total})


@bp.post("/products")
@require_authenticated
def create_product():
    return success_response(data=catalog.create_product(g.current_user, ProductIn.model_validate(_json()), request.remote_addr), status_code=201)


@bp.patch("/products/<int:product_id>")
@require_authenticated
def update_product(product_id: int):
    return success_response(data=catalog.update_product(g.current_user, product_id, ProductIn.model_validate(_json()), request.remote_addr))


@bp.delete("/products/<int:product_id>")
@require_authenticated
def delete_product(product_id: int):
    catalog.delete_product(g.current_user, product_id, request.remote_addr)
    return success_response(data={"id": product_id, "deleted": True})


@bp.get("/direct")
@require_authenticated
def list_direct():
    f = reports.parse_filters(request.args)
    page, per_page = parse_pagination(request.args)
    rows, total, amount = direct.list_direct(g.current_user, f, page=page, per_page=per_page, sort=request.args.get("sort", "purchase_date"),
                                             direction="asc" if request.args.get("direction") == "asc" else "desc")
    return success_response(data=rows, meta={"page": page, "per_page": per_page, "total": total, "total_amount": amount})


@bp.post("/direct")
@require_authenticated
def create_direct():
    return success_response(data=direct.create_direct(g.current_user, DirectIn.model_validate(_json()), request.remote_addr), status_code=201)


@bp.put("/direct/<int:direct_id>")
@require_authenticated
def update_direct(direct_id: int):
    return success_response(data=direct.update_direct(g.current_user, direct_id, DirectIn.model_validate(_json()), request.remote_addr))


@bp.delete("/direct/<int:direct_id>")
@require_authenticated
def delete_direct(direct_id: int):
    direct.delete_direct(g.current_user, direct_id, request.remote_addr)
    return success_response(data={"id": direct_id, "deleted": True})


@bp.post("/files")
@require_authenticated
def upload():
    row = services.upload_file(g.current_user, request.files.get("file"))
    return success_response(data=files.file_ref(row), status_code=201)


@bp.get("/files/<file_id>")
@require_authenticated
def download(file_id: str):
    services.require_any(g.current_user, services.READERS)
    row = files.get_file_or_404(file_id)
    resp = send_file(files.disk_path(row), as_attachment=True, download_name=row.original_name,
                     mimetype=row.content_type or "application/octet-stream")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@bp.get("")
@require_authenticated
def list_():
    f = reports.parse_filters(request.args)
    page, per_page = parse_pagination(request.args)
    rows, total = reports.list_requests(
        g.current_user, f, page=page, per_page=per_page, sort=request.args.get("sort", "created_at"),
        direction="asc" if request.args.get("direction") == "asc" else "desc", kpi=request.args.get("kpi") or None)
    return success_response(data=rows, meta={"page": page, "per_page": per_page, "total": total})


@bp.post("")
@require_authenticated
def create():
    req = services.create_request(g.current_user, BasicIn.model_validate(_json()), request.remote_addr)
    return _ok(req, 201)


@bp.get("/dashboard")
@require_authenticated
def dashboard():
    return success_response(data=reports.dashboard(g.current_user, reports.parse_filters(request.args)))


@bp.get("/export")
@require_authenticated
def export():
    """`format=xlsx` (default) downloads one report, or all six as sheets with `kind=all`;
    `format=json` returns the rows for the print / save-as-PDF view. Needs `export` AND `read`."""
    f = reports.parse_filters(request.args)
    kind = request.args.get("kind", "overview")
    fmt = (request.args.get("format") or "xlsx").lower()
    if kind == "all":
        if fmt == "json":
            raise InvalidInputError("برای چاپ، گزارش‌ها را یکی‌یکی دریافت کنید.", "kind")
        return _all_sheets(f)
    title, headers, rows = reports.export_table(g.current_user, kind, f)
    if fmt == "json":
        return success_response(data={"kind": kind, "title": title, "headers": headers, "rows": rows,
                                      "filters": _filters_text(f)})
    return _workbook([(title, headers, rows)], f"purchases-{kind}.xlsx")


def _filters_text(f) -> dict:
    from app.utils.jalali import format_jalali
    return {"date_from": format_jalali(f.date_from), "date_to": format_jalali(f.date_to), "unit": f.unit,
            "request_no": f.request_no, "item": f.item_q, "supplier": f.supplier_q,
            "category_id": f.category_id, "supplier_id": f.supplier_id, "statuses": [s.value for s in f.statuses],
            "review_statuses": [s.value for s in f.review_statuses]}


def _workbook(tables, filename: str):
    """One sheet per (title, headers, rows). Money columns (header ends with «(ریال)») get a 1,500,000 style format;
    the cell value stays a plain number."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    for title, headers, rows in tables:
        ws = wb.create_sheet(title[:31])
        ws.sheet_view.rightToLeft = True
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="F3F4F6")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for row in rows:
            ws.append([_safe(v) for v in row])
        for idx, h in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = min(max(12, len(str(h)) + 4), 40)
            if str(h).endswith("(ریال)"):
                for r in range(2, ws.max_row + 1):
                    ws.cell(row=r, column=idx).number_format = "#,##0"
        if title == reports.EXPORT_KINDS["overview"]:  # label/value layout: format the value of the rial rows
            for r in range(2, ws.max_row + 1):
                if "(ریال)" in str(ws.cell(row=r, column=1).value or ""):
                    ws.cell(row=r, column=2).number_format = "#,##0"
        ws.freeze_panes = "A2"
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(out, mimetype=XLSX_MIME, as_attachment=True, download_name=filename)


def _all_sheets(f):
    return _workbook([reports.export_table(g.current_user, k, f) for k in reports.EXPORT_KINDS], "purchases-all.xlsx")


@bp.get("/<int:request_id>")
@require_authenticated
def get_(request_id: int):
    return _ok(services.get_request(g.current_user, request_id))


def _step(name: str, schema, handler):
    def view(request_id: int):
        req = handler(g.current_user, request_id, schema.model_validate(_json()), request.remote_addr)
        return _ok(req)
    view.__name__ = f"save_{name}"
    return require_authenticated(view)


bp.add_url_rule("/<int:request_id>/basic", view_func=_step("basic", BasicIn, services.save_basic), methods=["PUT"])
bp.add_url_rule("/<int:request_id>/items", view_func=_step("items", ItemsIn, services.save_items), methods=["PUT"])
bp.add_url_rule("/<int:request_id>/budget", view_func=_step("budget", BudgetIn, services.save_budget), methods=["PUT"])
bp.add_url_rule("/<int:request_id>/inquiries", view_func=_step("inquiries", InquiriesIn, services.save_inquiries), methods=["PUT"])
bp.add_url_rule("/<int:request_id>/selection", view_func=_step("selection", SelectionIn, services.save_selection), methods=["PUT"])
bp.add_url_rule("/<int:request_id>/result", view_func=_step("result", ResultIn, services.save_result), methods=["PUT"])


@bp.post("/<int:request_id>/submit")
@require_authenticated
def submit(request_id: int):
    return _ok(services.submit(g.current_user, request_id, request.remote_addr))


@bp.post("/<int:request_id>/send-to-finance")
@require_authenticated
def send_to_finance(request_id: int):
    return _ok(services.send_to_finance(g.current_user, request_id, request.remote_addr))


@bp.post("/<int:request_id>/review")
@require_authenticated
def review(request_id: int):
    body = ReviewIn.model_validate(_json())
    return _ok(services.set_review_status(g.current_user, request_id, body.status, body.note, request.remote_addr))


@bp.post("/<int:request_id>/cancel")
@require_authenticated
def cancel(request_id: int):
    return _ok(services.cancel(g.current_user, request_id, NoteIn.model_validate(_json()).note, request.remote_addr))


@bp.post("/<int:request_id>/send-back")
@require_authenticated
def send_back(request_id: int):
    return _ok(services.send_back(g.current_user, request_id, NoteIn.model_validate(_json()).note, request.remote_addr))


@bp.post("/<int:request_id>/approve-reference")
@require_authenticated
def approve_reference(request_id: int):
    body = ApproveReferenceIn.model_validate(_json())
    return _ok(services.approve_reference(g.current_user, request_id, body, request.remote_addr))


@bp.delete("/<int:request_id>")
@require_authenticated
def delete_(request_id: int):
    services.delete_request(g.current_user, request_id, request.remote_addr)
    return success_response(data={"id": request_id, "deleted": True})
