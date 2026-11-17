"""Persian labels shared by the API (meta), the Excel export and the print view."""
STATUS = {
    "DRAFT": "پیش‌نویس", "ENTERING": "در حال ثبت اطلاعات", "AWAITING_INQUIRY": "در انتظار استعلام",
    "INQUIRING": "در حال استعلام", "AWAITING_SELECTION": "در انتظار انتخاب تأمین‌کننده",
    "PURCHASING": "در حال انجام خرید", "AWAITING_DELIVERY": "در انتظار تحویل", "COMPLETED": "تکمیل‌شده",
    "CANCELLED": "لغوشده", "NEEDS_REVISION": "نیازمند اصلاح اطلاعات",
}
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
EVENT_KIND = {"STEP": "ثبت مرحله", "STATUS": "تغییر وضعیت", "REFERENCE": "تأیید قیمت مبنا"}
