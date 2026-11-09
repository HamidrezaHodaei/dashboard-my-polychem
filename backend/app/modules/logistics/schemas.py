"""
Pydantic schemas for /api/logistics -- the registration wizard contract.

One schema per wizard step, so the same rules back both
`POST /public/validate-step` (per step, while the user moves through the
wizard) and the final `POST /public/register` / staff `POST /applicants`.

Payload shape (keys are the step ids from wizard.py):

    COMPANY: { applicant_type, company_info, representative, service_area }
    DRIVER : { applicant_type, identity,     contact, vehicle, service_area }

Dependency rules live next to the field they govern (field validators read
earlier fields through `info.data`, so declaration order matters), and are
mirrored declaratively in wizard.py for the frontend.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.modules.logistics import reference_data as ref
from app.modules.logistics import validators as v
from app.modules.logistics.validators import clean_text as v_clean
from app.modules.logistics.models import (
    ApplicantStatus, ApplicantType, AreaType, LegalType,
)


class _Strict(BaseModel):
    """Unknown keys are rejected -- e.g. vehicle fields sent for a company fail loudly."""

    model_config = ConfigDict(extra="forbid")


def raise_field_errors(title: str, errors: list[tuple[tuple, str, str]]):
    """Raise a pydantic ValidationError carrying (loc, code, message) items, so
    cross-section rules produce the same `details[{field,message}]` response."""
    raise ValidationError.from_exception_data(
        title,
        [{"type": PydanticCustomError(code, msg), "loc": loc, "input": None} for loc, code, msg in errors],
    )


def _dedupe(items: list) -> list:
    return list(dict.fromkeys(items))


# ---------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------
class FileRef(_Strict):
    """Pointer to an upload (POST /api/logistics/public/files)."""

    id: str = Field(..., min_length=1, max_length=36)
    name: str | None = Field(default=None, max_length=255)  # ignored: server re-reads it from the upload
    size: int | None = None


# ---------------------------------------------------------------------
# COMPANY path
# ---------------------------------------------------------------------
class CompanyInfoStep(_Strict):
    """Step 2 (company): اطلاعات شرکت."""

    entity_type: LegalType
    company_name: str | None = Field(default=None, validate_default=True)
    first_name: str | None = Field(default=None, validate_default=True)
    last_name: str | None = Field(default=None, validate_default=True)
    national_id: str | None = Field(default=None, validate_default=True)
    province: str
    city: str
    office_address: str

    @field_validator("company_name", mode="before")
    @classmethod
    def _company_name(cls, val, info):
        val = v.clean_text(val, max_len=255)
        kind = info.data.get("entity_type")
        if kind == LegalType.INDIVIDUAL:
            return None
        if kind == LegalType.LEGAL and not val:
            raise ValueError("Company name is required for a legal entity.")
        return val

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _person_name(cls, val, info):
        val = v.clean_text(val, max_len=100)
        kind = info.data.get("entity_type")
        if kind == LegalType.LEGAL:
            return None
        if kind == LegalType.INDIVIDUAL and not val:
            raise ValueError("First and last name are required for an individual.")
        return val

    @field_validator("national_id", mode="before")
    @classmethod
    def _national_id(cls, val, info):
        # شناسه ملی: optional, and only meaningful for a legal entity.
        if info.data.get("entity_type") == LegalType.INDIVIDUAL:
            return None
        return v.clean_legal_national_id(val)

    @field_validator("province", mode="before")
    @classmethod
    def _province(cls, val):
        val = v.clean_text(val, max_len=100)
        if not val or val not in ref.CITIES:
            raise ValueError("Pick a province from the list.")
        return val

    @field_validator("city", mode="before")
    @classmethod
    def _city(cls, val, info):
        val = v.clean_text(val, max_len=100)
        if not val:
            raise ValueError("City is required.")
        province = info.data.get("province")
        if province and not ref.city_in_province(province, val):
            raise ValueError("This city does not belong to the selected province.")
        return val

    @field_validator("office_address", mode="before")
    @classmethod
    def _address(cls, val):
        val = v.clean_text(val, max_len=1000)
        if not val or len(val) < 10:
            raise ValueError("Office address is required (at least 10 characters).")
        return val


class RepresentativeStep(_Strict):
    """Step 3 (company): نماینده و اطلاعات تماس."""

    first_name: str
    last_name: str
    position: str
    position_other: str | None = Field(default=None, validate_default=True)
    mobile: str
    landline: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _names(cls, val):
        val = v.clean_text(val, max_len=100)
        if not val:
            raise ValueError("This field is required.")
        return val

    @field_validator("position", mode="before")
    @classmethod
    def _position(cls, val):
        val = v.clean_text(val, max_len=30)
        if val not in ref.POSITION_CODES:
            raise ValueError("Pick a position from the list.")
        return val

    @field_validator("position_other", mode="before")
    @classmethod
    def _position_other(cls, val, info):
        val = v.clean_text(val, max_len=100)
        if info.data.get("position") == "OTHER":
            if not val:
                raise ValueError("Describe the position when you choose 'Other'.")
            return val
        return None

    @field_validator("mobile", mode="before")
    @classmethod
    def _mobile(cls, val):
        out = v.clean_mobile(val)
        if not out:
            raise ValueError("Mobile number is required.")
        return out

    @field_validator("landline", mode="before")
    @classmethod
    def _landline(cls, val):
        return v.clean_landline(val)


# ---------------------------------------------------------------------
# DRIVER path
# ---------------------------------------------------------------------
class IdentityStep(_Strict):
    """Step 2 (driver): اطلاعات هویتی."""

    first_name: str
    last_name: str
    national_code: str

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _names(cls, val):
        val = v.clean_text(val, max_len=100)
        if not val:
            raise ValueError("This field is required.")
        return val

    @field_validator("national_code", mode="before")
    @classmethod
    def _code(cls, val):
        out = v.clean_national_code(val)
        if not out:
            raise ValueError("National code is required.")
        return out


class ContactStep(_Strict):
    """Step 3 (driver): اطلاعات تماس."""

    mobile: str
    alt_phone: str | None = None

    @field_validator("mobile", mode="before")
    @classmethod
    def _mobile(cls, val):
        out = v.clean_mobile(val)
        if not out:
            raise ValueError("Mobile number is required.")
        return out

    @field_validator("alt_phone", mode="before")
    @classmethod
    def _alt(cls, val):
        return v.clean_mobile_or_landline(val)


class VehicleStep(_Strict):
    """Step 4 (driver ONLY): مشخصات وسیله نقلیه و بارگیر."""

    vehicle_type: str
    vehicle_type_other: str | None = Field(default=None, validate_default=True)
    body_type: str
    body_type_other: str | None = Field(default=None, validate_default=True)
    capacity_tons: float
    cargo_types: list[str] = Field(..., min_length=1)
    cargo_type_other: str | None = Field(default=None, validate_default=True)

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def _vehicle(cls, val):
        val = v.clean_text(val, max_len=20)
        if val not in ref.VEHICLE_TYPE_CODES:
            raise ValueError("Pick a vehicle type from the list.")
        return val

    @field_validator("vehicle_type_other", mode="before")
    @classmethod
    def _vehicle_other(cls, val, info):
        val = v.clean_text(val, max_len=100)
        if info.data.get("vehicle_type") == "OTHER":
            if not val:
                raise ValueError("Describe the vehicle type when you choose 'Other'.")
            return val
        return None

    @field_validator("body_type", mode="before")
    @classmethod
    def _body(cls, val):
        val = v.clean_text(val, max_len=20)
        if val not in ref.BODY_TYPE_CODES:
            raise ValueError("Pick a body type from the list.")
        return val

    @field_validator("body_type_other", mode="before")
    @classmethod
    def _body_other(cls, val, info):
        val = v.clean_text(val, max_len=100)
        if info.data.get("body_type") == "OTHER":
            if not val:
                raise ValueError("Describe the body type when you choose 'Other'.")
            return val
        return None

    @field_validator("capacity_tons", mode="before")
    @classmethod
    def _capacity(cls, val):
        if isinstance(val, bool) or val is None:
            raise ValueError("Capacity (tons) is required.")
        if isinstance(val, str):
            val = v.to_latin_digits(val).replace("٫", ".").replace(",", ".").strip()
        try:
            d = Decimal(str(val))
        except (InvalidOperation, ValueError):
            raise ValueError("Capacity must be a number.")
        if not d.is_finite() or d <= 0:
            raise ValueError("Capacity must be greater than zero.")
        if d > Decimal("100"):
            raise ValueError("Capacity cannot exceed 100 tons.")
        return float(d.quantize(Decimal("0.01")))

    @field_validator("cargo_types", mode="before")
    @classmethod
    def _cargo(cls, val):
        if not isinstance(val, list):
            raise ValueError("Pick at least one cargo type.")
        items = _dedupe([v.clean_text(x, max_len=20) for x in val])
        if not items:
            raise ValueError("Pick at least one cargo type.")
        bad = [x for x in items if x not in ref.CARGO_TYPE_CODES]
        if bad:
            raise ValueError("Unknown cargo type.")
        return items

    @field_validator("cargo_type_other", mode="before")
    @classmethod
    def _cargo_other(cls, val, info):
        val = v.clean_text(val, max_len=150)
        if "OTHER" in (info.data.get("cargo_types") or []):
            if not val:
                raise ValueError("Describe the cargo type when you choose 'Other'.")
            return val
        return None


# ---------------------------------------------------------------------
# Shared step: محدوده فعالیت
# ---------------------------------------------------------------------
class CoverageItem(_Strict):
    province: str
    all_cities: bool = False
    cities: list[str] = Field(default_factory=list)

    @field_validator("province", mode="before")
    @classmethod
    def _province(cls, val):
        val = v.clean_text(val, max_len=100)
        if not val or val not in ref.CITIES:
            raise ValueError("Pick a province from the list.")
        return val

    @field_validator("cities", mode="before")
    @classmethod
    def _cities(cls, val, info):
        if val is None:
            val = []
        if not isinstance(val, list):
            raise ValueError("Cities must be a list.")
        out = _dedupe([c for c in (v.clean_text(x, max_len=100) for x in val) if c])
        province = info.data.get("province")
        if province:
            for c in out:
                if not ref.city_in_province(province, c):
                    raise ValueError(f"'{c}' does not belong to {province}.")
        return out

    @model_validator(mode="after")
    def _cities_rule(self):
        # Whole-province coverage carries no city list; otherwise at least one city.
        if self.all_cities:
            self.cities = []
        elif not self.cities:
            raise ValueError("Pick at least one city or choose the whole province.")
        return self


class PermitIn(_Strict):
    type: str
    number: str | None = None
    expires_at: str | None = None
    file: FileRef | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _type(cls, val):
        val = v.clean_text(val, max_len=30)
        if val not in ref.PERMIT_TYPE_CODES:
            raise ValueError("Unknown permit type.")
        return val

    @field_validator("number", mode="before")
    @classmethod
    def _number(cls, val):
        return v.clean_text(val, max_len=100)

    @field_validator("expires_at", mode="before")
    @classmethod
    def _expires(cls, val):
        val = v.clean_text(val, max_len=10)
        return v.to_latin_digits(val) if val else None


def _country_list(val, label: str) -> list[str]:
    if not isinstance(val, list):
        raise ValueError(f"Pick at least one {label} country.")
    out = _dedupe([v.clean_text(x, max_len=2) for x in val])
    out = [c.upper() for c in out if c]
    if any(c not in ref.COUNTRY_CODES for c in out):
        raise ValueError("Unknown country.")
    return out


class ServiceAreaStep(_Strict):
    """Shared step: محدوده فعالیت. Fields not relevant to `area_type` are cleared
    (not rejected), so switching the type in the UI and re-saving always works."""

    area_type: AreaType
    coverage: list[CoverageItem] = Field(default_factory=list, validate_default=True)
    origin_countries: list[str] = Field(default_factory=list, validate_default=True)
    destination_countries: list[str] = Field(default_factory=list, validate_default=True)
    permits: list[PermitIn] = Field(default_factory=list, validate_default=True)

    @field_validator("coverage", mode="after")
    @classmethod
    def _coverage(cls, val, info):
        kind = info.data.get("area_type")
        if kind is None:
            return val
        names = [c.province for c in val]
        if len(set(names)) != len(names):
            raise ValueError("Each province can only be listed once.")
        if kind == AreaType.CITY:
            if len(val) != 1 or val[0].all_cities or len(val[0].cities) != 1:
                raise ValueError("Pick exactly one city for city-level activity.")
        elif kind == AreaType.PROVINCIAL:
            if len(val) != 1:
                raise ValueError("Pick exactly one province for provincial activity.")
        elif kind == AreaType.INTERPROVINCIAL:
            if len(val) < 2:
                raise ValueError("Pick at least two provinces for inter-provincial activity.")
        return val  # INTERNATIONAL: optional (e.g. border provinces)

    @field_validator("origin_countries", "destination_countries", mode="before")
    @classmethod
    def _countries(cls, val, info):
        kind = info.data.get("area_type")
        if kind is not None and kind != AreaType.INTERNATIONAL:
            return []
        label = "origin" if info.field_name == "origin_countries" else "destination"
        out = _country_list(val if val is not None else [], label)
        if kind == AreaType.INTERNATIONAL and not out:
            raise ValueError(f"Pick at least one {label} country.")
        return out

    @field_validator("permits", mode="after")
    @classmethod
    def _permits(cls, val, info):
        if info.data.get("area_type") != AreaType.INTERNATIONAL:
            return []
        types = [p.type for p in val]
        if len(set(types)) != len(types):
            raise ValueError("Each permit type can only be added once.")
        return val

    @model_validator(mode="after")
    def _area_rules(self):
        if self.area_type == AreaType.INTERNATIONAL:
            abroad = {c for c in self.origin_countries + self.destination_countries if c != "IR"}
            if not abroad:
                raise ValueError("International activity needs at least one country other than Iran.")
        else:
            self.origin_countries, self.destination_countries, self.permits = [], [], []
        return self


def check_permits(applicant_type: ApplicantType, area: ServiceAreaStep, *, loc_prefix: tuple = ("service_area",)):
    """Permit rules that depend on WHO is registering (can't live in the step model)."""
    if area.area_type != AreaType.INTERNATIONAL:
        return
    errors: list[tuple[tuple, str, str]] = []
    allowed = {p["code"]: p for p in ref.PERMIT_TYPES if p["for_type"] in ("BOTH", applicant_type.value)}
    present = {p.type: p for p in area.permits}
    for i, p in enumerate(area.permits):
        if p.type not in allowed:
            errors.append(((*loc_prefix, "permits", i, "type"), "permit_not_allowed",
                           "This permit type does not apply to this applicant type."))
    for code, meta in allowed.items():
        if meta["required"]:
            p = present.get(code)
            if p is None or p.file is None:
                errors.append(((*loc_prefix, "permits"), "permit_required",
                               f"The permit '{meta['label']}' (with its file) is required for international activity."))
    if errors:
        raise_field_errors("ServiceArea", errors)


# ---------------------------------------------------------------------
# Whole-registration payloads
# ---------------------------------------------------------------------
COMPANY_SECTIONS = ("company_info", "representative", "service_area")
DRIVER_SECTIONS = ("identity", "contact", "vehicle", "service_area")
SECTION_MODELS = {
    "company_info": CompanyInfoStep,
    "representative": RepresentativeStep,
    "identity": IdentityStep,
    "contact": ContactStep,
    "vehicle": VehicleStep,
    "service_area": ServiceAreaStep,
}


class RegistrationIn(_Strict):
    applicant_type: ApplicantType
    company_info: CompanyInfoStep | None = None
    representative: RepresentativeStep | None = None
    identity: IdentityStep | None = None
    contact: ContactStep | None = None
    vehicle: VehicleStep | None = None
    service_area: ServiceAreaStep | None = None


class AdminRegistrationIn(RegistrationIn):
    status: ApplicantStatus = ApplicantStatus.APPROVED
    # False = save as a draft: still the creator's to edit until they press "ثبت نهایی"
    is_finalized: bool = True


def parse_registration(raw: dict, model=RegistrationIn):
    """Validate a whole payload: shapes first (pydantic), then the rules that
    span sections -- which sections the chosen applicant type may/must send,
    and the type-dependent permit rule."""
    payload = model.model_validate(raw or {})
    wanted = COMPANY_SECTIONS if payload.applicant_type == ApplicantType.COMPANY else DRIVER_SECTIONS
    errors: list[tuple[tuple, str, str]] = []
    for name in SECTION_MODELS:
        sent = getattr(payload, name) is not None
        if name in wanted and not sent:
            errors.append(((name,), "section_required", "This section is required."))
        elif name not in wanted and sent:
            kind = "transport companies" if payload.applicant_type == ApplicantType.COMPANY else "drivers"
            errors.append(((name,), "section_not_allowed", f"This section does not apply to {kind}."))
    if errors:
        raise_field_errors("Registration", errors)
    check_permits(payload.applicant_type, payload.service_area)
    return payload


def validate_step(applicant_type: ApplicantType, step: str, data: dict) -> dict:
    """Validate ONE wizard step; returns the normalised step data."""
    wanted = COMPANY_SECTIONS if applicant_type == ApplicantType.COMPANY else DRIVER_SECTIONS
    if step not in wanted:
        raise_field_errors("Step", [(("step",), "unknown_step", "This step does not exist for this applicant type.")])
    model = SECTION_MODELS[step].model_validate(data or {})
    if step == "service_area":
        check_permits(applicant_type, model)
    return model.model_dump(mode="json")


class UpdateIn(_Strict):
    """Staff PATCH: each section sent REPLACES that whole section (validated as complete)."""

    company_info: CompanyInfoStep | None = None
    representative: RepresentativeStep | None = None
    identity: IdentityStep | None = None
    contact: ContactStep | None = None
    vehicle: VehicleStep | None = None
    service_area: ServiceAreaStep | None = None
    is_active: bool | None = None


class ReviewIn(_Strict):
    action: str = Field(..., pattern="^(APPROVE|REJECT|SUSPEND|REOPEN|REQUEST_EDIT)$")
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note", mode="before")
    @classmethod
    def _note(cls, val):
        return v.clean_text(val, max_len=1000)


class ChangeRequestIn(_Strict):
    """The creator of a finalised request asks the manager to allow a change."""

    reason: str = Field(..., min_length=3, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, v):
        out = v_clean(v, max_len=1000)
        if not out or len(out) < 3:
            raise ValueError("Explain why the information must be changed.")
        return out


class ValidateStepIn(_Strict):
    applicant_type: ApplicantType
    step: str
    data: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------
def _iso(dt: datetime | None):
    return dt.isoformat() if dt else None


def serialize_applicant(a, *, detail: bool = True) -> dict:
    """JSON-ready dict. List view (detail=False) leaves out the heavy sections."""
    out = {
        "id": a.id,
        "applicant_type": a.applicant_type.value,
        "status": a.status.value,
        "display_name": a.display_name,
        "mobile": a.mobile,
        "is_active": a.is_active,
        "is_public_submission": a.is_public_submission,
        "created_by_user_id": a.created_by_user_id,
        "created_by_name": a.created_by_name,
        "reviewed_by_user_id": a.reviewed_by_user_id,
        "reviewed_at": _iso(a.reviewed_at),
        "review_note": a.review_note,
        "is_finalized": a.is_finalized,
        "change_request_note": a.change_request_note,
        "change_requested_at": _iso(a.change_requested_at),
        "created_at": _iso(a.created_at),
        "updated_at": _iso(a.updated_at),
        "area_type": a.service_area.area_type.value if a.service_area else None,
    }
    c, d = a.company, a.driver
    if c:
        out["province"], out["city"] = c.province, c.city
    if d:
        out["vehicle_type"], out["body_type"], out["capacity_tons"] = d.vehicle_type, d.body_type, float(d.capacity_tons)
    if not detail:
        return out
    if c:
        out["company_info"] = {
            "entity_type": c.entity_type.value, "company_name": c.company_name, "first_name": c.first_name,
            "last_name": c.last_name, "national_id": c.national_id, "province": c.province, "city": c.city,
            "office_address": c.office_address,
        }
        out["representative"] = {
            "first_name": c.rep_first_name, "last_name": c.rep_last_name, "position": c.rep_position,
            "position_other": c.rep_position_other, "mobile": c.rep_mobile, "landline": c.rep_landline,
        }
    if d:
        out["identity"] = {"first_name": d.first_name, "last_name": d.last_name, "national_code": d.national_code}
        out["contact"] = {"mobile": d.mobile, "alt_phone": d.alt_phone}
        out["vehicle"] = {
            "vehicle_type": d.vehicle_type, "vehicle_type_other": d.vehicle_type_other,
            "body_type": d.body_type, "body_type_other": d.body_type_other,
            "capacity_tons": float(d.capacity_tons), "cargo_types": d.cargo_types,
            "cargo_type_other": d.cargo_type_other,
        }
    s = a.service_area
    if s:
        out["service_area"] = {
            "area_type": s.area_type.value, "coverage": s.coverage,
            "origin_countries": s.origin_countries, "destination_countries": s.destination_countries,
            "permits": s.permits,
        }
    return out
