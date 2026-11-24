"""
The notification catalogue: which category every notification `type` belongs to.

Categories are what the user switches on/off in Settings -> Notifications. A type that is not listed
here falls back to a prefix rule and finally to "other", so a new producer never silently disappears:
it is simply delivered under "other" until it is classified here.
"""
CATEGORIES: list[dict] = [
    {"key": "tasks", "label": "امور محوله", "description": "امور جدید، ارجاع و منشن"},
    {"key": "reminders", "label": "موعدها و یادآوری‌ها", "description": "نزدیک شدن یا گذشتن موعد، پیگیری مشتری و نمونه"},
    {"key": "purchases", "label": "درخواست‌های خرید", "description": "ثبت، استعلام، تأیید مدیر، پرداخت و تحویل"},
    {"key": "samples", "label": "درخواست نمونه", "description": "تأیید، ارسال، تحویل و بازخورد"},
    {"key": "reviews", "label": "بررسی و تأیید", "description": "نتیجه و درخواست بررسی ثبت‌ها (تأمین‌کننده، مشتری، لجستیک)"},
    {"key": "mail", "label": "مکاتبات", "description": "نامه‌های جدید"},
    {"key": "leave", "label": "مرخصی", "description": "درخواست و تأیید مرخصی"},
    {"key": "other", "label": "سایر", "description": "اعلان‌های عمومی"},
]
CATEGORY_KEYS = [c["key"] for c in CATEGORIES]

TYPE_CATEGORY: dict[str, str] = {
    "TASK_ASSIGNED": "tasks", "TASK_REFERRED": "tasks", "TASK_MENTION": "tasks",
    "TASK_DUE_SOON": "reminders", "TASK_OVERDUE": "reminders",
    "CUSTOMER_FOLLOWUP_DUE": "reminders", "CUSTOMER_FOLLOWUP_OVERDUE": "reminders",
    "SAMPLE_REMIND_SHIP": "reminders", "SAMPLE_REMIND_DELIVER": "reminders",
    "SAMPLE_REMIND_FOLLOWUP": "reminders", "SAMPLE_FOLLOWUP_DUE": "reminders",
    "REVIEW_RESULT": "reviews", "REVIEW_RESUBMITTED": "reviews", "CHANGE_REQUEST": "reviews",
    "REVIEW_REQUEST": "reviews",
    "MAIL": "mail",
}
PREFIX_CATEGORY = (("SAMPLE_", "samples"), ("PURCHASE_", "purchases"), ("LEAVE_", "leave"), ("TASK_", "tasks"))

# a pushed notification of these types is marked urgent for the push service (wakes a sleeping phone sooner)
HIGH_URGENCY = {"TASK_OVERDUE", "CUSTOMER_FOLLOWUP_OVERDUE", "PURCHASE_URGENT"}


def category_of(type_: str) -> str:
    if type_ in TYPE_CATEGORY:
        return TYPE_CATEGORY[type_]
    for prefix, cat in PREFIX_CATEGORY:
        if type_.startswith(prefix):
            return cat
    return "other"


def types_in(category: str) -> list[str]:
    """Explicitly classified types of one category (prefix-classified ones are matched with LIKE by the caller)."""
    return [t for t, c in TYPE_CATEGORY.items() if c == category]
