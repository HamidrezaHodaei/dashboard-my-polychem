"""
Service layer for /api/logistics -- Logistics module (transport companies + drivers).

Access control (the "سطح دسترسی" requirement) lives HERE, not in routes.py,
same as every other module. It is per applicant type, so a user can be
allowed to work with drivers but not companies (or vice versa):

    logistics.company.{read,create,update,delete,review}
    logistics.driver.{read,create,update,delete,review}

All checks are GLOBAL-only (scope_type/scope_id None), like Suppliers --
registrants don't belong to a department or team. `review` (approve /
reject / suspend) is deliberately a separate key from `update`: editing a
record and deciding on a registration are different responsibilities.

Public functions (`register_public`, `validate_public_step`, reference/wizard
getters, public upload) carry NO permission check by design; routes.py
rate-limits them.
"""
from datetime import datetime, timezone

from app.core import request_workflow as workflow
from app.core.audit_logs.services import write_audit_log
from app.core.users.models import User
from app.extensions import db
from app.modules.logistics import files, reference_data as ref, validators as v
from app.modules.notifications import services as notifications
from app.modules.logistics.models import (
    ApplicantStatus, ApplicantType, AreaType, LegalType, LogisticsApplicant, LogisticsCompanyProfile,
    LogisticsDriverProfile, LogisticsFile, LogisticsServiceArea,
)
from app.modules.logistics.schemas import (
    AdminRegistrationIn, ChangeRequestIn, RegistrationIn, ReviewIn, UpdateIn, check_permits, parse_registration,
    raise_field_errors, validate_step,
)
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "logistics"
_RESOURCE = {ApplicantType.COMPANY: "company", ApplicantType.DRIVER: "driver"}
ACTIONS = ("read", "create", "update", "delete", "review")


# ---------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------
def permission_key(applicant_type: ApplicantType, action: str) -> str:
    return f"logistics.{_RESOURCE[applicant_type]}.{action}"


def _can(actor: User, applicant_type: ApplicantType, action: str) -> bool:
    return has_permission(actor, permission_key(applicant_type, action), None, None)


def _require(actor: User, applicant_type: ApplicantType, action: str) -> None:
    key = permission_key(applicant_type, action)
    if not has_permission(actor, key, None, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def allowed_types(actor: User, action: str = "read") -> list[ApplicantType]:
    """Applicant types the actor may `action`. Empty list -> 403 for list-like endpoints."""
    return [t for t in ApplicantType if _can(actor, t, action)]


def _require_any(actor: User, action: str = "read") -> list[ApplicantType]:
    types = allowed_types(actor, action)
    if not types:
        raise PermissionDeniedError(
            "permission_denied", f"Missing permission 'logistics.company.{action}' or 'logistics.driver.{action}'."
        )
    return types


def require_file_read(actor: User) -> None:
    _require_any(actor, "read")


# ---------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------
def catalog() -> dict:
    return ref.public_catalog()


def validate_public_step(applicant_type: ApplicantType, step: str, data: dict) -> dict:
    """Validate one wizard step (no permission check -- public). Identity and
    contact steps also report duplicates early so the user needn't reach the end."""
    clean = validate_step(applicant_type, step, data)
    if step == "identity":
        _assert_unique_driver_code(clean["national_code"])
    elif step == "contact":
        _assert_unique_mobile(ApplicantType.DRIVER, clean["mobile"])
    elif step == "representative":
        _assert_unique_mobile(ApplicantType.COMPANY, clean["mobile"])
    elif step == "company_info" and clean.get("national_id"):
        _assert_unique_company_id(clean["national_id"])
    return clean


# ---------------------------------------------------------------------
# Duplicate guards (service-level: soft-deleted rows must not block re-registration)
# ---------------------------------------------------------------------
def _live():
    return db.session.query(LogisticsApplicant.id).filter(LogisticsApplicant.deleted_at.is_(None))


def _assert_unique_driver_code(code: str, *, exclude_id: int | None = None) -> None:
    q = _live().join(LogisticsDriverProfile, LogisticsDriverProfile.applicant_id == LogisticsApplicant.id).filter(
        LogisticsDriverProfile.national_code == code
    )
    if exclude_id:
        q = q.filter(LogisticsApplicant.id != exclude_id)
    if q.first():
        raise ConflictError("A driver with this national code is already registered.")


def _assert_unique_company_id(national_id: str, *, exclude_id: int | None = None) -> None:
    q = _live().join(LogisticsCompanyProfile, LogisticsCompanyProfile.applicant_id == LogisticsApplicant.id).filter(
        LogisticsCompanyProfile.national_id == national_id
    )
    if exclude_id:
        q = q.filter(LogisticsApplicant.id != exclude_id)
    if q.first():
        raise ConflictError("A company with this legal national ID is already registered.")


def _assert_unique_mobile(applicant_type: ApplicantType, mobile: str, *, exclude_id: int | None = None) -> None:
    q = _live().filter(LogisticsApplicant.applicant_type == applicant_type, LogisticsApplicant.mobile == mobile)
    if exclude_id:
        q = q.filter(LogisticsApplicant.id != exclude_id)
    if q.first():
        raise ConflictError("This mobile number is already registered.")


# ---------------------------------------------------------------------
# Building / applying sections
# ---------------------------------------------------------------------
def _resolve_file(ref_in: dict | None) -> dict | None:
    """Name/size always come from the upload record, never from the client."""
    if not ref_in:
        return None
    row = db.session.get(LogisticsFile, ref_in["id"])
    if row is None:
        raise ConflictError("An attached file was not found. Please upload it again.")
    return files.file_ref(row)


def _area_values(area) -> dict:
    d = area.model_dump(mode="json")
    permits = [{**p, "file": _resolve_file(p.get("file"))} for p in d["permits"]]
    return {
        "area_type": AreaType(d["area_type"]), "coverage": d["coverage"],
        "origin_countries": d["origin_countries"], "destination_countries": d["destination_countries"],
        "permits": permits,
    }


def _company_display(info) -> str:
    if info.entity_type == LegalType.LEGAL:
        return info.company_name
    return f"{info.first_name} {info.last_name}"


def _apply_company(profile: LogisticsCompanyProfile, info=None, rep=None) -> None:
    if info is not None:
        profile.entity_type = info.entity_type
        profile.company_name = info.company_name
        profile.first_name = info.first_name
        profile.last_name = info.last_name
        profile.national_id = info.national_id
        profile.province = info.province
        profile.city = info.city
        profile.office_address = info.office_address
    if rep is not None:
        profile.rep_first_name = rep.first_name
        profile.rep_last_name = rep.last_name
        profile.rep_position = rep.position
        profile.rep_position_other = rep.position_other
        profile.rep_mobile = rep.mobile
        profile.rep_landline = rep.landline


def _apply_driver(profile: LogisticsDriverProfile, identity=None, contact=None, vehicle=None) -> None:
    if identity is not None:
        profile.first_name, profile.last_name, profile.national_code = (
            identity.first_name, identity.last_name, identity.national_code,
        )
    if contact is not None:
        profile.mobile, profile.alt_phone = contact.mobile, contact.alt_phone
    if vehicle is not None:
        profile.vehicle_type = vehicle.vehicle_type
        profile.vehicle_type_other = vehicle.vehicle_type_other
        profile.body_type = vehicle.body_type
        profile.body_type_other = vehicle.body_type_other
        profile.capacity_tons = vehicle.capacity_tons
        profile.cargo_types = vehicle.cargo_types
        profile.cargo_type_other = vehicle.cargo_type_other


def _sync_denormalised(a: LogisticsApplicant) -> None:
    if a.applicant_type == ApplicantType.COMPANY:
        c = a.company
        a.display_name = c.company_name if c.entity_type == LegalType.LEGAL else f"{c.first_name} {c.last_name}"
        a.mobile = c.rep_mobile
    else:
        d = a.driver
        a.display_name = f"{d.first_name} {d.last_name}"
        a.mobile = d.mobile


def _assert_unique_for(payload, *, exclude_id: int | None = None) -> None:
    if payload.applicant_type == ApplicantType.COMPANY:
        _assert_unique_mobile(ApplicantType.COMPANY, payload.representative.mobile, exclude_id=exclude_id)
        if payload.company_info.national_id:
            _assert_unique_company_id(payload.company_info.national_id, exclude_id=exclude_id)
    else:
        _assert_unique_driver_code(payload.identity.national_code, exclude_id=exclude_id)
        _assert_unique_mobile(ApplicantType.DRIVER, payload.contact.mobile, exclude_id=exclude_id)


def _create(payload, *, status: ApplicantStatus, public: bool, actor: User | None, ip_address: str | None,
            is_finalized: bool = True):
    _assert_unique_for(payload)
    a = LogisticsApplicant(
        applicant_type=payload.applicant_type, status=status, is_public_submission=public,
        created_by_user_id=actor.id if actor else None, display_name="", mobile="", is_finalized=is_finalized,
    )
    if payload.applicant_type == ApplicantType.COMPANY:
        a.company = LogisticsCompanyProfile()
        _apply_company(a.company, payload.company_info, payload.representative)
    else:
        a.driver = LogisticsDriverProfile()
        _apply_driver(a.driver, payload.identity, payload.contact, payload.vehicle)
    a.service_area = LogisticsServiceArea(**_area_values(payload.service_area))
    _sync_denormalised(a)
    db.session.add(a)
    db.session.flush()
    write_audit_log(
        user_id=actor.id if actor else None, action="create", module=MODULE,
        entity_type=f"logistics_{_RESOURCE[a.applicant_type]}", entity_id=a.id,
        metadata={"source": "public_form" if public else "admin", "display_name": a.display_name},
        ip_address=ip_address,
    )
    db.session.commit()
    return a


def register_public(raw: dict, *, ip_address: str | None) -> LogisticsApplicant:
    """No permission check -- the public wizard's final submit. Always lands as PENDING."""
    payload = parse_registration(raw, RegistrationIn)
    return _create(payload, status=ApplicantStatus.PENDING, public=True, actor=None, ip_address=ip_address)


def create_admin(actor: User, raw: dict, *, ip_address: str | None) -> LogisticsApplicant:
    payload = parse_registration(raw, AdminRegistrationIn)
    _require(actor, payload.applicant_type, "create")
    status = payload.status
    if not payload.is_finalized:
        status = ApplicantStatus.PENDING  # a draft is never "decided"
    elif status != ApplicantStatus.PENDING:
        # Deciding a registration's outcome is the `review` permission, even when adding by hand.
        _require(actor, payload.applicant_type, "review")
    return _create(
        payload, status=status, public=False, actor=actor, ip_address=ip_address, is_finalized=payload.is_finalized
    )


# ---------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------
def _get_or_404(applicant_id: int) -> LogisticsApplicant:
    a = db.session.get(LogisticsApplicant, applicant_id)
    if a is None or a.deleted_at is not None:
        raise NotFoundError(f"Applicant {applicant_id} was not found.")
    return a


def get_applicant(actor: User, applicant_id: int) -> LogisticsApplicant:
    a = _get_or_404(applicant_id)
    _require(actor, a.applicant_type, "read")
    return a


def list_applicants(
    actor: User, *, page: int, per_page: int, applicant_type: str = "", search: str = "", status: str = "",
    province: str = "", area_type: str = "", vehicle_type: str = "", body_type: str = "",
    include_inactive: bool = False,
):
    types = _require_any(actor, "read")
    if applicant_type:
        try:
            wanted = ApplicantType(applicant_type)
        except ValueError:
            return [], 0
        _require(actor, wanted, "read")
        types = [wanted]

    q = (
        db.session.query(LogisticsApplicant)
        .outerjoin(LogisticsCompanyProfile, LogisticsCompanyProfile.applicant_id == LogisticsApplicant.id)
        .outerjoin(LogisticsDriverProfile, LogisticsDriverProfile.applicant_id == LogisticsApplicant.id)
        .outerjoin(LogisticsServiceArea, LogisticsServiceArea.applicant_id == LogisticsApplicant.id)
        .filter(LogisticsApplicant.deleted_at.is_(None), LogisticsApplicant.applicant_type.in_(types))
    )
    if not include_inactive:
        q = q.filter(LogisticsApplicant.is_active.is_(True))
    if status:
        q = q.filter(LogisticsApplicant.status == status)
    if province:
        q = q.filter(LogisticsCompanyProfile.province == province)
    if area_type:
        q = q.filter(LogisticsServiceArea.area_type == area_type)
    if vehicle_type:
        q = q.filter(LogisticsDriverProfile.vehicle_type == vehicle_type)
    if body_type:
        q = q.filter(LogisticsDriverProfile.body_type == body_type)
    term = (search or "").strip()
    if term:
        latin = v.to_latin_digits(term)
        text = f"%{(v.clean_text(term) or term).lower()}%"
        q = q.filter(db.or_(
            db.func.lower(LogisticsApplicant.display_name).like(text),
            LogisticsApplicant.mobile.like(f"%{latin}%"),
            LogisticsDriverProfile.national_code.like(f"%{latin}%"),
            LogisticsCompanyProfile.national_id.like(f"%{latin}%"),
        ))
    return paginate_query(q.order_by(LogisticsApplicant.id.desc()), page, per_page)


def stats(actor: User) -> dict:
    types = _require_any(actor, "read")
    base = db.session.query(LogisticsApplicant).filter(
        LogisticsApplicant.deleted_at.is_(None), LogisticsApplicant.applicant_type.in_(types)
    )
    by_type_status: dict = {t.value: {s.value: 0 for s in ApplicantStatus} for t in types}
    for t, s, n in (
        db.session.query(LogisticsApplicant.applicant_type, LogisticsApplicant.status, db.func.count(LogisticsApplicant.id))
        .filter(LogisticsApplicant.deleted_at.is_(None), LogisticsApplicant.applicant_type.in_(types))
        .group_by(LogisticsApplicant.applicant_type, LogisticsApplicant.status)
    ):
        by_type_status[t.value][s.value] = n
    by_area = {a.value: 0 for a in AreaType}
    for area, n in (
        db.session.query(LogisticsServiceArea.area_type, db.func.count(LogisticsServiceArea.id))
        .join(LogisticsApplicant, LogisticsApplicant.id == LogisticsServiceArea.applicant_id)
        .filter(LogisticsApplicant.deleted_at.is_(None), LogisticsApplicant.applicant_type.in_(types))
        .group_by(LogisticsServiceArea.area_type)
    ):
        by_area[area.value] = n
    return {"total": base.count(), "by_type_status": by_type_status, "by_area_type": by_area}


# ---------------------------------------------------------------------
# Update / review / delete
# ---------------------------------------------------------------------
_COMPANY_ONLY = ("company_info", "representative")
_DRIVER_ONLY = ("identity", "contact", "vehicle")


def update_applicant(actor: User, applicant_id: int, payload: UpdateIn, *, ip_address: str | None) -> LogisticsApplicant:
    a = _get_or_404(applicant_id)
    as_manager = _can(actor, a.applicant_type, "update")
    if not as_manager and not _creator_can_edit(actor, a):
        # not a manager, and not the creator inside the editable part of the workflow
        _require(actor, a.applicant_type, "update")
    if not as_manager:
        payload.is_active = None  # operational switches stay with managers
    forbidden = _DRIVER_ONLY if a.applicant_type == ApplicantType.COMPANY else _COMPANY_ONLY
    errors = [
        ((name,), "section_not_allowed", "This section does not apply to this applicant type.")
        for name in forbidden if getattr(payload, name) is not None
    ]
    if errors:
        raise_field_errors("Update", errors)
    if payload.service_area is not None:
        check_permits(a.applicant_type, payload.service_area)

    changed = [k for k in payload.model_fields_set if getattr(payload, k) is not None]
    if a.applicant_type == ApplicantType.COMPANY:
        _apply_company(a.company, payload.company_info, payload.representative)
        if payload.representative is not None:
            _assert_unique_mobile(ApplicantType.COMPANY, payload.representative.mobile, exclude_id=a.id)
        if payload.company_info is not None and payload.company_info.national_id:
            _assert_unique_company_id(payload.company_info.national_id, exclude_id=a.id)
    else:
        _apply_driver(a.driver, payload.identity, payload.contact, payload.vehicle)
        if payload.identity is not None:
            _assert_unique_driver_code(payload.identity.national_code, exclude_id=a.id)
        if payload.contact is not None:
            _assert_unique_mobile(ApplicantType.DRIVER, payload.contact.mobile, exclude_id=a.id)
    if payload.service_area is not None:
        vals = _area_values(payload.service_area)
        for key, value in vals.items():  # whole section replaced, so a changed area_type drops stale fields
            setattr(a.service_area, key, value)
    if payload.is_active is not None:
        a.is_active = payload.is_active
    _sync_denormalised(a)

    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=f"logistics_{_RESOURCE[a.applicant_type]}",
        entity_id=a.id, metadata={"changed_sections": changed}, ip_address=ip_address,
    )
    db.session.commit()
    return a


# review action -> {current status: next status}. The four request statuses are shared with
# suppliers and customers (core/request_workflow.py); SUSPENDED is an extra state of approved parties.
_TRANSITIONS = {
    **{k: dict(v_) for k, v_ in workflow.TRANSITIONS.items()},
    "SUSPEND": {workflow.APPROVED: "SUSPENDED"},
}
_TRANSITIONS["APPROVE"] = {**_TRANSITIONS["APPROVE"], "SUSPENDED": workflow.APPROVED}
_NOTE_REQUIRED = workflow.NOTE_REQUIRED | {"SUSPEND"}


def _creator_can_edit(actor: User, a: LogisticsApplicant) -> bool:
    return workflow.creator_can_edit(
        created_by_user_id=a.created_by_user_id, actor_id=actor.id, status=a.status.value, is_finalized=a.is_finalized
    )


def viewer_flags(actor: User, a: LogisticsApplicant) -> dict:
    """What THIS user may do with the record (the UI shows buttons from this; the server re-checks)."""
    manager = _can(actor, a.applicant_type, "update")
    mine = a.created_by_user_id == actor.id
    return {
        "can_edit": manager or _creator_can_edit(actor, a),
        "can_finalize": (manager or mine) and (
            a.status == ApplicantStatus.NEEDS_EDIT or (a.status == ApplicantStatus.PENDING and not a.is_finalized)
        ),
        "can_request_change": workflow.can_request_change(
            created_by_user_id=a.created_by_user_id, actor_id=actor.id, status=a.status.value, is_finalized=a.is_finalized
        ) and a.change_request_note is None,
        "can_review": _can(actor, a.applicant_type, "review"),
    }


def review_applicant(actor: User, applicant_id: int, payload: ReviewIn, *, ip_address: str | None) -> LogisticsApplicant:
    a = _get_or_404(applicant_id)
    _require(actor, a.applicant_type, "review")
    if payload.action in _NOTE_REQUIRED and not payload.note:
        raise_field_errors("Review", [(("note",), "note_required", "A written reason is required for this decision.")])
    if not a.is_finalized:
        raise ConflictError("This request is still a draft: its creator has not submitted it yet.")
    nxt = _TRANSITIONS[payload.action].get(a.status.value)
    if nxt is None:
        raise ConflictError(f"Cannot {payload.action.lower()} an applicant whose status is {a.status.value}.")
    previous = a.status
    a.status = ApplicantStatus(nxt)
    a.reviewed_by_user_id = actor.id
    a.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    a.review_note = payload.note
    a.change_request_note = a.change_requested_at = None  # the request has been answered
    if a.created_by_user_id and a.created_by_user_id != actor.id and payload.action in workflow.TRANSITIONS:
        title, body = workflow.review_notification(payload.action, a.display_name, payload.note)
        notifications.notify(a.created_by_user_id, "REVIEW_RESULT", title, body, link="/procurement/logistics")
    write_audit_log(
        user_id=actor.id, action=f"review_{payload.action.lower()}", module=MODULE,
        entity_type=f"logistics_{_RESOURCE[a.applicant_type]}", entity_id=a.id,
        metadata={"from": previous.value, "to": a.status.value}, ip_address=ip_address,
    )
    db.session.commit()
    return a


def finalize_applicant(actor: User, applicant_id: int, *, ip_address: str | None) -> LogisticsApplicant:
    """ثبت نهایی / ثبت مجدد: the creator submits the draft, or re-submits after corrections --
    either way the request goes (back) to «در انتظار بررسی»."""
    a = _get_or_404(applicant_id)
    if not (a.created_by_user_id == actor.id or _can(actor, a.applicant_type, "update")):
        raise PermissionDeniedError("permission_denied", "Only the creator of this request can submit it.")
    if not (a.status == ApplicantStatus.NEEDS_EDIT or (a.status == ApplicantStatus.PENDING and not a.is_finalized)):
        raise ConflictError("This request is already submitted.")
    resubmission = a.status == ApplicantStatus.NEEDS_EDIT
    a.status = ApplicantStatus(workflow.after_finalize(a.status.value))
    a.is_finalized = True
    write_audit_log(
        user_id=actor.id, action="resubmit" if resubmission else "finalize", module=MODULE,
        entity_type=f"logistics_{_RESOURCE[a.applicant_type]}", entity_id=a.id, ip_address=ip_address,
    )
    if resubmission and a.reviewed_by_user_id and a.reviewed_by_user_id != actor.id:
        notifications.notify(
            a.reviewed_by_user_id, "REVIEW_RESUBMITTED", "درخواست پس از اصلاح دوباره ثبت شد",
            f"«{a.display_name}» پس از اعمال اصلاحات دوباره برای بررسی ثبت شد.", link="/procurement/logistics",
        )
    db.session.commit()
    return a


def request_change(actor: User, applicant_id: int, payload: ChangeRequestIn, *, ip_address: str | None) -> LogisticsApplicant:
    """The creator of a finalised request asks the manager to allow a change (reason required)."""
    a = _get_or_404(applicant_id)
    if not workflow.can_request_change(
        created_by_user_id=a.created_by_user_id, actor_id=actor.id, status=a.status.value, is_finalized=a.is_finalized
    ):
        raise PermissionDeniedError("permission_denied", "You cannot request a change for this record.")
    a.change_request_note = payload.reason
    a.change_requested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    write_audit_log(
        user_id=actor.id, action="change_request", module=MODULE,
        entity_type=f"logistics_{_RESOURCE[a.applicant_type]}", entity_id=a.id, ip_address=ip_address,
    )
    if a.reviewed_by_user_id and a.reviewed_by_user_id != actor.id:
        notifications.notify(
            a.reviewed_by_user_id, "CHANGE_REQUEST", "درخواست تغییر اطلاعات",
            f"{actor.full_name} برای «{a.display_name}» درخواست تغییر اطلاعات ثبت کرد: {payload.reason}",
            link="/procurement/logistics",
        )
    db.session.commit()
    return a


def delete_applicant(actor: User, applicant_id: int, *, ip_address: str | None) -> None:
    a = _get_or_404(applicant_id)
    _require(actor, a.applicant_type, "delete")
    a.deleted_at = datetime.now(timezone.utc)
    a.is_active = False
    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=f"logistics_{_RESOURCE[a.applicant_type]}",
        entity_id=a.id, ip_address=ip_address,
    )
    db.session.commit()
