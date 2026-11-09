"""
Declarative description of the registration wizard (served by
GET /api/logistics/public/wizard).

This is what lets the frontend render the steps WITHOUT hard-coding the
rules: which steps each applicant type sees, every field's label / widget /
required-ness, when a field is shown (`visible_when`) or becomes mandatory
(`required_when`), and its format. The authoritative enforcement is still
schemas.py -- this file only *describes* it, and tests/modules/test_logistics.py
checks the two stay in step for the main rules.

Condition syntax (all conditions refer to a field in the SAME step):
    {"field": "entity_type", "equals": "LEGAL"}
    {"field": "cargo_types", "includes": "OTHER"}
    {"field": "area_type",   "in": ["PROVINCIAL", "INTERPROVINCIAL"]}
"""


def _f(name, label, type_, *, required=False, **extra) -> dict:
    return {"name": name, "label": label, "type": type_, "required": required, **extra}


_NAME = {"max_length": 100}
_MOBILE = {"format": "ir_mobile", "example": "09121234567"}
_LANDLINE = {"format": "ir_landline", "example": "02122334455", "help": "همراه با کد شهر"}

CHOOSE_TYPE_STEP = {
    "id": "applicant_type",
    "title": "نوع متقاضی",
    "description": "ثبت‌نام را به‌عنوان شرکت حمل‌ونقل یا راننده انجام دهید.",
    "fields": [
        _f("applicant_type", "نوع متقاضی", "card_select", required=True,
           options=[{"code": "COMPANY", "label": "شرکت حمل‌ونقل"}, {"code": "DRIVER", "label": "راننده"}]),
    ],
}

COMPANY_INFO_STEP = {
    "id": "company_info",
    "title": "اطلاعات شرکت",
    "fields": [
        _f("entity_type", "نوع شخصیت", "radio", required=True, options_ref="legal_types"),
        _f("company_name", "نام شرکت", "text", visible_when={"field": "entity_type", "equals": "LEGAL"},
           required_when={"field": "entity_type", "equals": "LEGAL"}, max_length=255),
        _f("first_name", "نام", "text", visible_when={"field": "entity_type", "equals": "INDIVIDUAL"},
           required_when={"field": "entity_type", "equals": "INDIVIDUAL"}, **_NAME),
        _f("last_name", "نام خانوادگی", "text", visible_when={"field": "entity_type", "equals": "INDIVIDUAL"},
           required_when={"field": "entity_type", "equals": "INDIVIDUAL"}, **_NAME),
        _f("national_id", "شناسه ملی", "text", visible_when={"field": "entity_type", "equals": "LEGAL"},
           format="ir_legal_national_id", length=11, help="اختیاری؛ در صورت ورود، ۱۱ رقم و معتبر باشد."),
        _f("province", "استان محل فعالیت", "select", required=True, options_ref="provinces"),
        _f("city", "شهر محل فعالیت", "select", required=True, options_ref="provinces.cities",
           depends_on="province", help="با تغییر استان، شهر پاک می‌شود."),
        _f("office_address", "نشانی دفتر", "textarea", required=True, min_length=10, max_length=1000),
    ],
}

REPRESENTATIVE_STEP = {
    "id": "representative",
    "title": "نماینده و اطلاعات تماس",
    "fields": [
        _f("first_name", "نام نماینده", "text", required=True, **_NAME),
        _f("last_name", "نام خانوادگی نماینده", "text", required=True, **_NAME),
        _f("position", "سمت نماینده", "select", required=True, options_ref="representative_positions"),
        _f("position_other", "عنوان سمت", "text", visible_when={"field": "position", "equals": "OTHER"},
           required_when={"field": "position", "equals": "OTHER"}, max_length=100),
        _f("mobile", "شماره موبایل", "tel", required=True, **_MOBILE),
        _f("landline", "تلفن ثابت", "tel", **_LANDLINE),
    ],
}

IDENTITY_STEP = {
    "id": "identity",
    "title": "اطلاعات هویتی",
    "fields": [
        _f("first_name", "نام", "text", required=True, **_NAME),
        _f("last_name", "نام خانوادگی", "text", required=True, **_NAME),
        _f("national_code", "کد ملی", "text", required=True, format="ir_national_code", length=10),
    ],
}

CONTACT_STEP = {
    "id": "contact",
    "title": "اطلاعات تماس",
    "fields": [
        _f("mobile", "شماره موبایل", "tel", required=True, **_MOBILE),
        _f("alt_phone", "تلفن جایگزین", "tel", format="ir_mobile_or_landline"),
    ],
}

VEHICLE_STEP = {
    "id": "vehicle",
    "title": "مشخصات وسیله نقلیه و بارگیر",
    "only_for": "DRIVER",
    "fields": [
        _f("vehicle_type", "نوع خودرو", "select", required=True, options_ref="vehicle_types"),
        _f("vehicle_type_other", "نوع خودرو (سایر)", "text", visible_when={"field": "vehicle_type", "equals": "OTHER"},
           required_when={"field": "vehicle_type", "equals": "OTHER"}, max_length=100),
        _f("body_type", "نوع بارگیر / اتاق", "select", required=True, options_ref="body_types"),
        _f("body_type_other", "نوع بارگیر (سایر)", "text", visible_when={"field": "body_type", "equals": "OTHER"},
           required_when={"field": "body_type", "equals": "OTHER"}, max_length=100),
        _f("capacity_tons", "ظرفیت حمل (تن)", "number", required=True, min=0.01, max=100, decimals=2),
        _f("cargo_types", "نوع کالاهای قابل حمل", "multiselect", required=True, min_items=1, options_ref="cargo_types"),
        _f("cargo_type_other", "نوع کالا (سایر)", "text", visible_when={"field": "cargo_types", "includes": "OTHER"},
           required_when={"field": "cargo_types", "includes": "OTHER"}, max_length=150),
    ],
}

_INTL = {"field": "area_type", "equals": "INTERNATIONAL"}
SERVICE_AREA_STEP = {
    "id": "service_area",
    "title": "محدوده فعالیت",
    "shared": True,
    "description": "برای هر دو گروه یکسان است؛ داده‌ها برای هر متقاضی جداگانه ذخیره می‌شود.",
    "fields": [
        _f("area_type", "نوع محدوده فعالیت", "radio", required=True, options_ref="area_types"),
        _f("coverage", "استان‌ها و شهرهای تحت پوشش", "coverage_picker",
           visible_when={"field": "area_type", "in": ["CITY", "PROVINCIAL", "INTERPROVINCIAL", "INTERNATIONAL"]},
           required_when={"field": "area_type", "in": ["CITY", "PROVINCIAL", "INTERPROVINCIAL"]},
           item={"province": "select", "all_cities": "boolean", "cities": "multiselect(province)"},
           rules_by_area_type={
               "CITY": {"provinces": {"min": 1, "max": 1}, "cities_per_province": {"exactly": 1}, "whole_province": False},
               "PROVINCIAL": {"provinces": {"min": 1, "max": 1}, "cities_per_province": {"min": 1}, "whole_province": True},
               "INTERPROVINCIAL": {"provinces": {"min": 2}, "cities_per_province": {"min": 1}, "whole_province": True},
               "INTERNATIONAL": {"provinces": {"min": 0}, "optional": True, "whole_province": True},
           }),
        _f("origin_countries", "کشورهای مبدأ", "multiselect", visible_when=_INTL, required_when=_INTL,
           min_items=1, options_ref="countries"),
        _f("destination_countries", "کشورهای مقصد", "multiselect", visible_when=_INTL, required_when=_INTL,
           min_items=1, options_ref="countries",
           help="حداقل یک کشور غیر از ایران در مبدأ یا مقصد لازم است."),
        _f("permits", "مجوزهای بین‌المللی", "permit_list", visible_when=_INTL,
           options_ref="permit_types", item={"type": "select", "number": "text", "expires_at": "text", "file": "file"},
           help="مجوزهای الزامی بر اساس نوع متقاضی در permit_types (required / for_type) مشخص شده‌اند."),
    ],
    "on_area_type_change": "فیلدهای نامرتبط با نوع جدید پاک می‌شوند؛ سرور نیز آن‌ها را نادیده می‌گیرد/پاک می‌کند.",
}


def build_wizard() -> dict:
    company_steps = [COMPANY_INFO_STEP, REPRESENTATIVE_STEP, SERVICE_AREA_STEP]
    driver_steps = [IDENTITY_STEP, CONTACT_STEP, VEHICLE_STEP, SERVICE_AREA_STEP]

    def numbered(steps):
        # Step 1 is always the type chooser, so the type-specific steps start at 2.
        return [{**s, "number": i} for i, s in enumerate([CHOOSE_TYPE_STEP, *steps], start=1)]

    return {
        "first_step": CHOOSE_TYPE_STEP,
        "paths": {"COMPANY": numbered(company_steps), "DRIVER": numbered(driver_steps)},
        "payload_keys": {
            "COMPANY": ["company_info", "representative", "service_area"],
            "DRIVER": ["identity", "contact", "vehicle", "service_area"],
        },
        "notes": [
            "مرحلهٔ vehicle فقط در مسیر راننده وجود دارد و ارسال آن برای شرکت حمل‌ونقل رد می‌شود.",
            "هر مرحله را می‌توان با POST /api/logistics/public/validate-step جداگانه اعتبارسنجی کرد.",
        ],
        "catalog_url": "/api/logistics/public/reference",
    }


WIZARD = build_wizard()
