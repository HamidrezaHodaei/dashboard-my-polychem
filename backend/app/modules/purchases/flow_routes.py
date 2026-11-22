"""
/api/purchases/flow -- the item-based purchase flow (warehouse -> procurement -> manager -> finance -> delivery).
Every handler only parses the body; permissions and rules are in flow.py.

    GET    /meta                                  pick lists, labels, allowed times, my permissions
    GET    /options?kind=  POST /options  PATCH|DELETE /options/<id>        requesting units / request types (settings)
    GET    /sla            PUT /sla                                         allowed delivery time per priority (settings)
    GET    /requests?queue=&status=&item_status=&unit=&q=&page=             list / cartables
    POST   /requests                              register (warehouse)
    GET    /requests/<id>      PUT /requests/<id>                           detail / edit after «استرداد جهت اصلاح»
    POST   /requests/<id>/status                  {status, note}  procurement
    PUT    /requests/<id>/items/<item>/supply-place        {supply_place}
    POST   /requests/<id>/items/<item>/quotes     PUT|DELETE .../quotes/<quote>
    POST   /requests/<id>/submit-to-manager       {item_ids}
    POST   /requests/<id>/items/<item>/decision   {action: APPROVE|RETURN, quote_id, note}  manager
    POST   /requests/<id>/items/<item>/payment    finance
    POST   /requests/<id>/finance-return          {item_ids?}  finance -> procurement
    POST   /requests/<id>/items/<item>/status     {status: SHIPPING|DELIVERED|CANCELLED, note, file_id}
    POST   /requests/<id>/items/<item>/receipt    {file_id}
    GET    /kpi?date_from=&date_to=&unit=&priority=        GET /kpi/export
"""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.modules.purchases import flow
from app.modules.purchases.flow_schemas import (
    FinanceReturnIn, FlowRequestIn, ItemStatusIn, ManagerDecisionIn, OptionIn, PaymentIn, QuoteIn, ReceiptIn,
    SlaIn, StatusIn, SubmitItemsIn, SupplyPlaceIn,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("purchase_flow", __name__, url_prefix="/api/purchases/flow")


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _ok(req, status_code: int = 200):
    return success_response(data=flow.request_dict(g.current_user, req), status_code=status_code)


@bp.get("/meta")
@require_authenticated
def meta():
    return success_response(data=flow.meta(g.current_user))


@bp.get("/options")
@require_authenticated
def options():
    return success_response(data=flow.list_options(g.current_user, request.args.get("kind")))


@bp.post("/options")
@require_authenticated
def create_option():
    return success_response(data=flow.create_option(g.current_user, OptionIn.model_validate(_json()), request.remote_addr), status_code=201)


@bp.patch("/options/<int:option_id>")
@require_authenticated
def update_option(option_id: int):
    return success_response(data=flow.update_option(g.current_user, option_id, OptionIn.model_validate(_json()), request.remote_addr))


@bp.delete("/options/<int:option_id>")
@require_authenticated
def delete_option(option_id: int):
    flow.delete_option(g.current_user, option_id, request.remote_addr)
    return success_response(data={"id": option_id, "deleted": True})


@bp.get("/sla")
@require_authenticated
def get_sla():
    flow.S.require_any(g.current_user, flow.S.READERS)
    return success_response(data=flow.meta(g.current_user)["sla"])


@bp.put("/sla")
@require_authenticated
def put_sla():
    return success_response(data=flow.save_sla(g.current_user, SlaIn.model_validate(_json()), request.remote_addr))


@bp.get("/requests")
@require_authenticated
def list_():
    page, per_page = parse_pagination(request.args)
    rows, total = flow.list_requests(g.current_user, request.args, page, per_page)
    return success_response(data=rows, meta={"page": page, "per_page": per_page, "total": total})


@bp.post("/requests")
@require_authenticated
def create():
    return _ok(flow.create_request(g.current_user, FlowRequestIn.model_validate(_json()), request.remote_addr), 201)


@bp.get("/requests/<int:request_id>")
@require_authenticated
def get_(request_id: int):
    return _ok(flow.get_request(g.current_user, request_id))


@bp.put("/requests/<int:request_id>")
@require_authenticated
def update(request_id: int):
    return _ok(flow.update_request(g.current_user, request_id, FlowRequestIn.model_validate(_json()), request.remote_addr))


@bp.post("/requests/<int:request_id>/status")
@require_authenticated
def set_status(request_id: int):
    body = StatusIn.model_validate(_json())
    return _ok(flow.set_status(g.current_user, request_id, body.status, body.note, request.remote_addr))


@bp.put("/requests/<int:request_id>/items/<int:item_id>/supply-place")
@require_authenticated
def supply_place(request_id: int, item_id: int):
    body = SupplyPlaceIn.model_validate(_json())
    return _ok(flow.set_supply_place(g.current_user, request_id, item_id, body.supply_place, request.remote_addr))


@bp.post("/requests/<int:request_id>/items/<int:item_id>/quotes")
@require_authenticated
def add_quote(request_id: int, item_id: int):
    body = QuoteIn.model_validate({**_json(), "id": None})
    return _ok(flow.save_quote(g.current_user, request_id, item_id, body, request.remote_addr), 201)


@bp.put("/requests/<int:request_id>/items/<int:item_id>/quotes/<int:quote_id>")
@require_authenticated
def edit_quote(request_id: int, item_id: int, quote_id: int):
    body = QuoteIn.model_validate({**_json(), "id": quote_id})
    return _ok(flow.save_quote(g.current_user, request_id, item_id, body, request.remote_addr))


@bp.delete("/requests/<int:request_id>/items/<int:item_id>/quotes/<int:quote_id>")
@require_authenticated
def remove_quote(request_id: int, item_id: int, quote_id: int):
    return _ok(flow.delete_quote(g.current_user, request_id, item_id, quote_id, request.remote_addr))


@bp.post("/requests/<int:request_id>/submit-to-manager")
@require_authenticated
def to_manager(request_id: int):
    body = SubmitItemsIn.model_validate(_json())
    return _ok(flow.submit_to_manager(g.current_user, request_id, body.item_ids, request.remote_addr))


@bp.post("/requests/<int:request_id>/items/<int:item_id>/decision")
@require_authenticated
def decision(request_id: int, item_id: int):
    return _ok(flow.manager_decide(g.current_user, request_id, item_id, ManagerDecisionIn.model_validate(_json()), request.remote_addr))


@bp.post("/requests/<int:request_id>/items/<int:item_id>/payment")
@require_authenticated
def payment(request_id: int, item_id: int):
    return _ok(flow.record_payment(g.current_user, request_id, item_id, PaymentIn.model_validate(_json()), request.remote_addr))


@bp.post("/requests/<int:request_id>/finance-return")
@require_authenticated
def finance_return(request_id: int):
    return _ok(flow.finance_return(g.current_user, request_id, FinanceReturnIn.model_validate(_json()), request.remote_addr))


@bp.post("/requests/<int:request_id>/items/<int:item_id>/status")
@require_authenticated
def item_status(request_id: int, item_id: int):
    return _ok(flow.set_item_status(g.current_user, request_id, item_id, ItemStatusIn.model_validate(_json()), request.remote_addr))


@bp.post("/requests/<int:request_id>/items/<int:item_id>/receipt")
@require_authenticated
def receipt(request_id: int, item_id: int):
    body = ReceiptIn.model_validate(_json())
    return _ok(flow.upload_receipt(g.current_user, request_id, item_id, body.file_id, request.remote_addr))


@bp.get("/kpi")
@require_authenticated
def kpi():
    return success_response(data=flow.kpi(g.current_user, request.args))


@bp.get("/kpi/export")
@require_authenticated
def kpi_export():
    from app.modules.purchases.routes import _workbook
    title, headers, rows = flow.kpi_export(g.current_user, request.args)
    return _workbook([(title, headers, rows)], "purchase-timing-kpi.xlsx")
