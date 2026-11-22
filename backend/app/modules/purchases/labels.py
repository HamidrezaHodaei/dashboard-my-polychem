"""Persian labels shared by the API (meta), the Excel export and the print view."""
STATUS = {
    "DRAFT": "پیش‌نویس", "ENTERING": "در حال ثبت اطلاعات", "AWAITING_INQUIRY": "در انتظار استعلام",
    "INQUIRING": "در حال استعلام", "AWAITING_SELECTION": "در انتظار انتخاب تأمین‌کننده",
    "PURCHASING": "در حال انجام خرید", "SENT_TO_FINANCE": "ارسال به مالی",
    "AWAITING_DELIVERY": "در حال تحویل و حمل", "COMPLETED": "پایان‌یافته",
    "CANCELLED": "لغوشده", "NEEDS_REVISION": "نیازمند اصلاح اطلاعات",
}
REVIEW = {"PENDING_REVIEW": "در انتظار بررسی", "APPROVED": "تأیید شده", "REJECTED": "رد شده", "NEEDS_REVISION": "نیازمند اصلاح"}
PRIORITY = {"NORMAL": "عادی", "URGENT": "فوری", "EMERGENCY": "اضطراری"}
DELIVERY = {"NOT_DELIVERED": "تحویل نشده", "PARTIAL": "تحویل جزئی", "DELIVERED": "تحویل کامل"}
REFERENCE_SOURCE = {
    "LAST_PURCHASE": "قیمت آخرین خرید ثبت‌شده در سامانه", "CONTRACT": "قرارداد یا تعرفه تأییدشده",
    "PRICE_LIST": "لیست قیمت رسمی یا پیش‌فاکتور مبنا", "OTHER": "سایر (با ذکر مستند)",
}
SELECTION_REASON = {
    "LOWEST_PRICE": "کمترین قیمت", "QUALITY": "کیفیت", "DELIVERY_TIME": "زمان تحویل",
    "PAYMENT_TERMS": "شرایط پرداخت", "OTHER": "سایر موارد",
}
STEP = {
    "basic": "اطلاعات اولیه", "items": "اقلام کالا", "budget": "بودجه و برآورد",
    "inquiries": "استعلام قیمت", "selection": "انتخاب تأمین‌کننده", "result": "نتیجه و تکمیل خرید",
}
EVENT_KIND = {"STEP": "ثبت مرحله", "STATUS": "تغییر وضعیت", "REFERENCE": "تأیید قیمت مبنا", "REVIEW": "وضعیت بررسی"}

# ── item-based flow (flow.py) ────────────────────────────────────────
FLOW_STATUS = {
    "UNDER_REVIEW": "در حال بررسی", "SOURCING": "در حال استعلام و تأمین", "REFERRED_FINANCE": "ارجاع استعلام به مالی",
    "FOLLOW_UP": "پیگیری پرداخت و حمل", "PARTIAL_DELIVERY": "تحویل داده‌شده – جزئی",
    "COMPLETED": "تحویل داده‌شده – بسته", "RETURNED": "استرداد جهت اصلاح", "VOID": "ابطال",
}
ITEM_STATUS = {
    "PENDING": "در انتظار بررسی", "INQUIRY": "در حال استعلام و تأمین", "AWAITING_APPROVAL": "منتظر تأیید مدیر",
    "IN_FINANCE": "در انتظار پرداخت (مالی)", "PAID": "پرداخت‌شده", "SHIPPING": "در حال حمل",
    "DELIVERED": "تحویل داده‌شده", "CANCELLED": "ابطال",
}
FLOW_PRIORITY = {"NORMAL": "عادی", "URGENT": "فوری", "EMERGENCY": "خیلی فوری"}
SUPPLY_PLACE = {"LOCAL": "محلی", "NON_LOCAL": "غیرمحلی"}
SUBJECT = {"ASSET": "دارایی", "GENERAL": "عمومی"}
PAY_METHOD = {"CASH": "نقدی", "CHEQUE": "چکی"}
SLA_UNIT = {"DAYS": "روز", "HOURS": "ساعت"}
