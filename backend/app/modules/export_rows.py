"""Rows for the Excel / Word exports. Each `*_table(...)` returns (title, headers, rows).

Who may export is decided by the `<module>.<resource>.export` permission (sales: `crm.sale.export`);
the caller must ALSO hold `read`, because the rows come from the same filtered list the screen shows.
"""
from datetime import datetime

from app.core.creator_snapshot import display_name as creator_display
from app.core.users.models import User
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.jalali import format_jalali, to_tehran

COMMERCIAL = {
    "NO_ACTION": "بدون اقدام", "MARKETING_NEGOTIATION": "در حال مذاکره و بازاریابی", "SAMPLE_SENT": "ارسال نمونه",
    "AWAITING_SAMPLE_APPROVAL": "منتظر تایید نمونه", "SALES_NEGOTIATION": "در حال مذاکره فروش",
    "ACQUIRED": "مشتری جذب شده", "REPEAT_ACTIVE": "مشتری تکرار شونده - فعال",
    "INACTIVE_LOST": "غیرفعال - از دست رفته", "POTENTIAL": "بالقوه",
}
REVIEW = {"PENDING": "در انتظار بررسی", "APPROVED": "تأیید", "REJECTED": "رد درخواست",
          "NEEDS_EDIT": "نیازمند ویرایش", "SUSPENDED": "تعلیق"}
PARTY_TYPE = {"LEGAL": "شخص حقوقی", "INDIVIDUAL": "شخص حقیقی"}
SUPPLIER_STATUS = {"ACTIVE": "فعال", "SEMI_ACTIVE": "نیمه‌فعال", "INACTIVE": "غیرفعال"}
QUALITY = {"EXCELLENT": "عالی", "MEDIUM": "متوسط", "WEAK": "ضعیف"}
APPLICANT = {"COMPANY": "شرکت حمل‌ونقل", "DRIVER": "راننده"}
SALE_TYPE = {"OFFICIAL": "رسمی", "UNOFFICIAL": "غیررسمی"}
SALE_STATUS = {"PROCESSING": "در حال پردازش", "COMPLETED": "تکمیل شده"}


def require_export(actor: User, key: str) -> None:
    if not has_permission(actor, key, None, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _val(x):
    return getattr(x, "value", x)


def stamp(dt: datetime | None) -> str:
    """Jalali date + Tehran time, e.g. 1405/08/18 14:32 -- the moment a record was registered."""
    if dt is None:
        return ""
    local = to_tehran(dt)
    return f"{format_jalali(local.date())} {local:%H:%M}"


def _people(contacts) -> tuple[str, str]:
    contacts = contacts or []
    names = "، ".join(f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() for c in contacts if isinstance(c, dict))
    phones = "، ".join(str(c.get("mobile") or c.get("landline") or "") for c in contacts if isinstance(c, dict))
    return names, phones


def customers_table(customers) -> tuple[str, list[str], list[list]]:
    headers = ["نام مشتری", "نوع", "برند", "صنعت", "استان", "شهر", "افراد تماس", "شماره تماس", "وضعیت تجاری",
               "وضعیت درخواست", "مسئول پیگیری", "ثبت‌کننده", "تاریخ و ساعت ثبت"]
    rows = []
    for c in customers:
        names, phones = _people(c.contacts)
        industries = "، ".join(
            " / ".join(p for p in (i.get("category"), i.get("subcategory")) if p)
            for i in (c.industries or []) if isinstance(i, dict)
        )
        rows.append([
            c.display_name, PARTY_TYPE.get(_val(c.customer_type), ""), c.brand_name or "", industries,
            c.factory_province or "", c.factory_city or "", names, phones,
            COMMERCIAL.get(_val(c.commercial_status), ""), REVIEW.get(c.review_status, ""),
            getattr(c, "assigned_to_name", "") or "", creator_display(c) or "", stamp(c.created_at),
        ])
    return "بانک مشتریان", headers, rows


def suppliers_table(suppliers) -> tuple[str, list[str], list[list]]:
    headers = ["نام تأمین‌کننده", "نوع", "دسته", "زیردسته", "افراد تماس", "شماره تماس", "وضعیت", "کیفیت",
               "وضعیت درخواست", "ثبت‌کننده", "تاریخ و ساعت ثبت"]
    rows = []
    for s in suppliers:
        names, phones = _people(s.contacts)
        rows.append([
            s.display_name, PARTY_TYPE.get(_val(s.supplier_type), ""), s.category or "", s.subcategory or "",
            names, phones, SUPPLIER_STATUS.get(_val(s.status), ""), QUALITY.get(_val(s.quality), "") if s.quality else "",
            REVIEW.get(s.review_status, ""), creator_display(s) or "", stamp(s.created_at),
        ])
    return "تأمین‌کنندگان", headers, rows


def logistics_table(applicants) -> tuple[str, list[str], list[list]]:
    headers = ["نام", "نوع", "موبایل", "وضعیت", "ثبت از فرم عمومی", "ثبت‌کننده", "تاریخ و ساعت ثبت"]
    rows = [[
        a.display_name, APPLICANT.get(_val(a.applicant_type), ""), a.mobile, REVIEW.get(_val(a.status), ""),
        "بله" if a.is_public_submission else "خیر", creator_display(a) or "", stamp(a.created_at),
    ] for a in applicants]
    return "لجستیک", headers, rows


def sales_table(sales: list[dict]) -> tuple[str, list[str], list[list]]:
    headers = ["تاریخ", "مشتری", "استان", "گرید", "مقدار (کیلوگرم)", "فی (ریال)", "مبلغ خالص (ریال)", "نوع سند",
               "نوع فروش", "پرداخت", "وضعیت", "توضیحات", "ثبت‌کننده", "تاریخ و ساعت ثبت"]
    rows = []
    for s in sales:
        rows.append([
            s["date"], s["customer"].get("label") or s["customer"]["name"], s["customer"].get("province") or "", s["product"]["name"],
            s["net_quantity_kg"], s["unit_price"], s["net_amount"],
            "برگشت از فروش" if s["is_return"] else "فاکتور فروش", SALE_TYPE.get(s["sale_type"], ""),
            (s["payment_method"] or {}).get("name", ""), SALE_STATUS.get(s["status"], ""), s["description"] or "",
            s.get("created_by_name") or "", s.get("created_at_display") or "",
        ])
    return "گزارش فروش", headers, rows


REQUEST_SAMPLE_STATUS = {
    "DRAFT": "پیش‌نویس", "NEW_REQUEST": "درخواست جدید", "PENDING_APPROVAL": "در انتظار تأیید", "APPROVED": "تأیید شده",
    "REJECTED": "رد شده", "ON_HOLD": "متوقف", "DISPATCHED": "ارسال شده", "AWAITING_FEEDBACK": "در انتظار بازخورد",
    "COMPLETED": "تکمیل شده", "CONVERTED": "تبدیل به فروش", "CANCELLED": "لغو شده",
}
REQUEST_SAMPLE_PRIORITY = {"LOW": "کم", "NORMAL": "عادی", "HIGH": "زیاد", "URGENT": "فوری"}
REQUEST_SAMPLE_FEEDBACK = {
    "ACCEPTED": "تأیید شد", "REJECTED": "تأیید نشد", "ACCEPTED_WITH_CONDITIONS": "تأیید مشروط",
    "UNDER_EVALUATION": "در حال بررسی", "NO_RESPONSE": "بدون پاسخ",
}


def request_samples_table(rows: list[dict]) -> tuple[str, list[str], list[list]]:
    headers = ["شناسه", "مشتری", "محصول", "گرید", "مقدار نمونه", "تاریخ ثبت", "کارشناس فروش", "اولویت", "وضعیت",
               "بازخورد مشتری", "شمارهٔ حواله", "ثبت‌کننده"]
    data = [[
        r["code"], r["customer"]["name"], r["product"] or "", r["grade"] or "", r["quantity_label"],
        format_jalali(datetime.fromisoformat(r["requested_date"]).date()), r["sales_rep"]["name"] or "",
        REQUEST_SAMPLE_PRIORITY.get(r["priority"], ""), REQUEST_SAMPLE_STATUS.get(r["status"], ""),
        REQUEST_SAMPLE_FEEDBACK.get(r["feedback_status"] or "", ""), r["dispatch_ref_number"] or "", r["created_by_name"] or "",
    ] for r in rows]
    return "درخواست نمونه محصول", headers, data
