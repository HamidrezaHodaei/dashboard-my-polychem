"""Dict shapes returned by the API (money as numbers, dates as ISO + Jalali)."""
from app.modules.purchases import labels as L
from app.modules.purchases import services as S
from app.utils.jalali import format_jalali, to_tehran


def _d(value):
    return value.isoformat() if value else None


def _j(value):
    return format_jalali(value) if value else None


def _stamp(dt):
    if dt is None:
        return None
    local = to_tehran(dt)
    return f"{format_jalali(local.date())} {local:%H:%M}"


def item_dict(req, item) -> dict:
    est = None if item.estimated_unit_price is None else S.num(S._dec(item.quantity) * S._dec(item.estimated_unit_price))
    sav = S.item_savings(item) if req.status.value == "COMPLETED" else None
    return {
        "id": item.id, "position": item.position, "product_id": item.product_id, "product_code": item.product_code,
        "category_id": item.category_id, "category_name": item.category_name,
        "name": item.name, "specs": item.specs, "brand_model": item.brand_model,
        "quantity": S.num(item.quantity), "unit": item.unit,
        "estimated_unit_price": S.num(item.estimated_unit_price), "estimated_total": est,
        "reference_unit_price": S.num(item.reference_unit_price),
        "reference_source": item.reference_source.value if item.reference_source else None,
        "reference_note": item.reference_note, "reference_item_id": item.reference_item_id,
        "reference_approved": item.reference_approved_at is not None,
        "reference_approved_at": _stamp(item.reference_approved_at),
        "final_unit_price": S.num(item.final_unit_price), "purchased_quantity": S.num(item.purchased_quantity),
        "final_total": None if item.final_unit_price is None or item.purchased_quantity is None
        else S.num(S._dec(item.final_unit_price) * S._dec(item.purchased_quantity)),
        "savings": S.num(sav),
    }


def inquiry_dict(req, inq, lowest) -> dict:
    complete = S.inquiry_lines_complete(req, inq)
    return {
        "id": inq.id, "position": inq.position, "supplier_id": inq.supplier_id, "supplier_name": inq.supplier_name,
        "received_date": _d(inq.received_date), "received_date_jalali": _j(inq.received_date),
        "validity_days": inq.validity_days, "delivery_days": inq.delivery_days, "payment_terms": inq.payment_terms,
        "extra_costs": S.num(inq.extra_costs), "total_price": S.num(inq.total_price), "lines_complete": complete,
        "is_lowest": bool(complete and lowest is not None and S._dec(inq.total_price) == lowest),
        "is_selected": inq.id == req.selected_inquiry_id, "note": inq.note,
        "file": {"id": inq.file.id, "name": inq.file.original_name, "size": inq.file.size} if inq.file else None,
        "lines": [{"item_id": ln.item_id, "unit_price": S.num(ln.unit_price)} for ln in inq.lines],
    }


def events_for(request_id: int) -> list[dict]:
    from sqlalchemy import select
    from app.extensions import db
    from app.modules.purchases.models import PurchaseEvent

    rows = db.session.scalars(select(PurchaseEvent).where(PurchaseEvent.request_id == request_id)
                              .order_by(PurchaseEvent.created_at, PurchaseEvent.id)).all()
    return [{
        "id": e.id, "kind": e.kind, "kind_label": L.EVENT_KIND.get(e.kind, e.kind),
        "step": e.step, "step_label": L.STEP.get(e.step) if e.step else None,
        "from_status": e.from_status, "from_label": (L.REVIEW if e.kind == "REVIEW" else L.STATUS).get(e.from_status) if e.from_status else None,
        "to_status": e.to_status, "to_label": (L.REVIEW if e.kind == "REVIEW" else L.STATUS).get(e.to_status) if e.to_status else None,
        "note": e.note, "user_name": e.user_name, "at": _stamp(e.created_at),
    } for e in rows]


def request_dict(req, actor=None) -> dict:
    lowest = S.lowest_inquiry_total(req)
    est = S.estimated_total(req)
    savings = [S.item_savings(i) for i in req.items] if req.status.value == "COMPLETED" else []
    counted = [s for s in savings if s is not None]
    data = {
        "id": req.id, "request_no": req.request_no, "status": req.status.value, "status_label": L.STATUS[req.status.value],
        "status_note": req.status_note,
        "review_status": req.review_status.value, "review_label": L.REVIEW[req.review_status.value],
        "review_note": req.review_note, "reviewed_at": _stamp(req.reviewed_at), "reviewed_by_name": req.reviewed_by_name,
        "pipeline_status": S.pipeline_status(req).value,
        "sent_to_finance_at": _stamp(req.sent_to_finance_at), "current_step": req.current_step,
        "requester_unit": req.requester_unit, "requester_name": req.requester_name,
        "request_date": _d(req.request_date), "request_date_jalali": _j(req.request_date),
        "subject": req.subject, "priority": req.priority.value, "priority_label": L.PRIORITY[req.priority.value],
        "reason": req.reason, "description": req.description,
        "budget_amount": S.num(req.budget_amount), "estimated_total": S.num(est),
        "required_date": _d(req.required_date), "required_date_jalali": _j(req.required_date),
        "delivery_location": req.delivery_location, "budget_files": req.budget_files or [],
        "inquiry_shortfall_reason": req.inquiry_shortfall_reason,
        "inquiries_finalized": req.inquiries_finalized_at is not None,
        "selected_inquiry_id": req.selected_inquiry_id,
        "selection_reasons": req.selection_reasons or [],
        "selection_reason_labels": [L.SELECTION_REASON.get(r, r) for r in (req.selection_reasons or [])],
        "selection_note": req.selection_note,
        "purchase_date": _d(req.purchase_date), "purchase_date_jalali": _j(req.purchase_date),
        "final_extra_costs": S.num(req.final_extra_costs), "final_amount": S.num(req.final_amount),
        "delivery_status": req.delivery_status.value, "delivery_label": L.DELIVERY[req.delivery_status.value],
        "completion_note": req.completion_note, "final_files": req.final_files or [],
        "completed_at": _stamp(req.completed_at),
        "savings": S.num(sum(counted, S.ZERO)) if counted else None,
        "savings_items_counted": len(counted), "items_count": len(req.items),
        "creator_name": req.creator_name or req.creator_display, "created_at": _stamp(req.created_at),
        "updated_at": _stamp(req.updated_at),
        "items": [item_dict(req, i) for i in req.items],
        "inquiries": [inquiry_dict(req, q, lowest) for q in req.inquiries],
        "events": events_for(req.id),
    }
    if actor is not None:
        data["my_actions"] = S.viewer_flags(actor, req)
    return data
