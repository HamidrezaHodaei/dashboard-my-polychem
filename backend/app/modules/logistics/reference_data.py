"""
Static reference catalogs for the logistics wizard (single source of truth).

Everything the wizard offers in a select/multi-select lives here, with the
Persian label shown to users. The API accepts only the machine `code`
(except provinces/cities, which are stored by name -- same convention as
Supplier.category / Customer.factory_province).

`OTHER` entries ("سایر") exist for vehicle type, body type, cargo type and
representative position; choosing one makes the matching `*_other` free
text field required (see wizard.py `required_when`).

CITIES is the list of main cities per province (county seats and major
towns). It is deliberately a plain dict so it can be extended or replaced
with a full national division list without touching any other file.
"""

VEHICLE_TYPES = [
    ("PICKUP", "وانت"),
    ("LIGHT_TRUCK", "کامیونت"),
    ("TRUCK", "کامیون"),
    ("TRACTOR", "کشنده"),
    ("TRAILER", "تریلی"),
    ("TEN_WHEEL", "ده‌چرخ"),
    ("OTHER", "سایر"),
]

BODY_TYPES = [
    ("ENCLOSED", "مسقف"),
    ("TARP", "چادری"),
    ("FLATBED", "کفی"),
    ("REFRIGERATED", "یخچال‌دار"),
    ("TANKER", "تانکر"),
    ("DUMP", "کمپرسی"),
    ("CONTAINER_CARRIER", "کانتینربر"),
    ("CAR_CARRIER", "خودروبر"),
    ("LIVESTOCK", "دام‌بر"),
    ("LOWBED", "کمرشکن"),
    ("BULK_SILO", "فله‌بر / سیلو"),
    ("OTHER", "سایر"),
]

CARGO_TYPES = [
    ("FOOD", "مواد غذایی"),
    ("PERISHABLE", "کالای فاسدشدنی / سردخانه‌ای"),
    ("AGRICULTURAL", "محصولات کشاورزی"),
    ("LIVESTOCK", "دام و طیور"),
    ("CONSTRUCTION", "مصالح ساختمانی"),
    ("METAL", "فلزات و آهن‌آلات"),
    ("CHEMICAL", "مواد شیمیایی و پتروشیمی"),
    ("PETROLEUM", "فرآورده‌های نفتی"),
    ("HAZARDOUS", "مواد خطرناک"),
    ("MACHINERY", "ماشین‌آلات و تجهیزات"),
    ("CONSUMER", "کالای مصرفی و لوازم خانگی"),
    ("HOUSEHOLD", "اثاثیه منزل و اداری"),
    ("PHARMA", "دارو و تجهیزات پزشکی"),
    ("CONTAINER", "کانتینر"),
    ("BULK", "کالای فله"),
    ("OTHER", "سایر"),
]

AREA_TYPES = [
    ("CITY", "شهری"),
    ("PROVINCIAL", "استانی"),
    ("INTERPROVINCIAL", "بین‌استانی"),
    ("INTERNATIONAL", "بین‌المللی"),
]

LEGAL_TYPES = [("INDIVIDUAL", "حقیقی"), ("LEGAL", "حقوقی")]

REPRESENTATIVE_POSITIONS = [
    ("CEO", "مدیرعامل"),
    ("BOARD_MEMBER", "عضو هیئت‌مدیره"),
    ("OWNER", "مالک / صاحب‌امتیاز"),
    ("OPERATIONS_MANAGER", "مدیر عملیات"),
    ("TRANSPORT_MANAGER", "مدیر حمل‌ونقل"),
    ("DISPATCHER", "مسئول توزیع / ترافیک"),
    ("EXPERT", "کارشناس"),
    ("OTHER", "سایر"),
]

# Permit catalog. `for_type` = which applicant type must supply it when the
# service area is INTERNATIONAL; `required` = mandatory for that type.
PERMIT_TYPES = [
    {"code": "INTL_TRANSPORT_LICENSE", "label": "پروانه فعالیت حمل‌ونقل بین‌المللی",
     "for_type": "COMPANY", "required": True},
    {"code": "INTL_DRIVER_PERMIT", "label": "کارت / مجوز رانندگی بین‌المللی",
     "for_type": "DRIVER", "required": True},
    {"code": "TIR_CARNET", "label": "کارنه تیر (TIR)", "for_type": "BOTH", "required": False},
    {"code": "CMR_INSURANCE", "label": "بیمه‌نامه CMR", "for_type": "BOTH", "required": False},
    {"code": "OTHER_PERMIT", "label": "سایر مجوزها", "for_type": "BOTH", "required": False},
]

COUNTRIES = [
    ("IR", "ایران"), ("IQ", "عراق"), ("TR", "ترکیه"), ("AM", "ارمنستان"), ("AZ", "جمهوری آذربایجان"),
    ("TM", "ترکمنستان"), ("AF", "افغانستان"), ("PK", "پاکستان"), ("GE", "گرجستان"),
    ("KZ", "قزاقستان"), ("UZ", "ازبکستان"), ("KG", "قرقیزستان"), ("TJ", "تاجیکستان"),
    ("RU", "روسیه"), ("BY", "بلاروس"), ("AE", "امارات متحده عربی"), ("OM", "عمان"),
    ("KW", "کویت"), ("QA", "قطر"), ("BH", "بحرین"), ("SA", "عربستان سعودی"),
    ("SY", "سوریه"), ("LB", "لبنان"), ("JO", "اردن"), ("CN", "چین"), ("IN", "هند"),
    ("BG", "بلغارستان"), ("RO", "رومانی"), ("GR", "یونان"), ("DE", "آلمان"),
]

CITIES = {
    "آذربایجان شرقی": ["تبریز", "مراغه", "مرند", "اهر", "میانه", "شبستر", "بناب", "سراب", "جلفا", "هادیشهر"],
    "آذربایجان غربی": ["ارومیه", "خوی", "میاندوآب", "بوکان", "مهاباد", "سلماس", "پیرانشهر", "نقده", "ماکو", "اشنویه"],
    "اردبیل": ["اردبیل", "پارس‌آباد", "مشگین‌شهر", "خلخال", "گرمی", "بیله‌سوار", "نمین", "نیر"],
    "اصفهان": ["اصفهان", "کاشان", "نجف‌آباد", "خمینی‌شهر", "شاهین‌شهر", "فلاورجان", "مبارکه", "زرین‌شهر", "گلپایگان", "نطنز", "اردستان", "سمیرم"],
    "البرز": ["کرج", "فردیس", "نظرآباد", "اشتهارد", "طالقان", "ساوجبلاغ", "محمدشهر", "ماهدشت"],
    "ایلام": ["ایلام", "دهلران", "آبدانان", "ایوان", "مهران", "دره‌شهر", "سرابله"],
    "بوشهر": ["بوشهر", "برازجان", "کنگان", "گناوه", "جم", "عسلویه", "دیر", "خورموج", "بندر دیلم"],
    "تهران": ["تهران", "شهریار", "اسلامشهر", "ورامین", "پاکدشت", "قدس", "ملارد", "بهارستان", "رباط‌کریم", "پردیس", "دماوند", "فیروزکوه", "قرچک", "پیشوا"],
    "چهارمحال و بختیاری": ["شهرکرد", "بروجن", "فارسان", "لردگان", "هفشجان", "سامان"],
    "خراسان جنوبی": ["بیرجند", "قائن", "طبس", "فردوس", "نهبندان", "سرایان", "بشرویه"],
    "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت‌حیدریه", "کاشمر", "قوچان", "تربت‌جام", "تایباد", "چناران", "گناباد", "سرخس", "درگز"],
    "خراسان شمالی": ["بجنورد", "شیروان", "اسفراین", "آشخانه", "جاجرم", "فاروج"],
    "خوزستان": ["اهواز", "آبادان", "خرمشهر", "دزفول", "ماهشهر", "بندر امام خمینی", "اندیمشک", "شوشتر", "بهبهان", "ایذه", "شادگان", "رامهرمز", "مسجدسلیمان"],
    "زنجان": ["زنجان", "ابهر", "خرمدره", "قیدار", "طارم", "ماهنشان"],
    "سمنان": ["سمنان", "شاهرود", "دامغان", "گرمسار", "مهدی‌شهر", "ایوانکی"],
    "سیستان و بلوچستان": ["زاهدان", "چابهار", "زابل", "ایرانشهر", "سراوان", "خاش", "کنارک", "نیک‌شهر", "میرجاوه"],
    "فارس": ["شیراز", "مرودشت", "جهرم", "فسا", "کازرون", "لار", "داراب", "فیروزآباد", "آباده", "اقلید", "نی‌ریز", "لامرد", "ممسنی"],
    "قزوین": ["قزوین", "البرز", "تاکستان", "بوئین‌زهرا", "آبیک", "محمدیه", "الوند"],
    "قم": ["قم"],
    "کردستان": ["سنندج", "سقز", "بانه", "مریوان", "قروه", "بیجار", "کامیاران", "دیواندره"],
    "کرمان": ["کرمان", "رفسنجان", "سیرجان", "جیرفت", "بم", "زرند", "کهنوج", "بردسیر", "شهربابک", "راور"],
    "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "سرپل ذهاب", "کنگاور", "سنقر", "صحنه", "هرسین", "جوانرود", "پاوه", "قصرشیرین"],
    "کهگیلویه و بویراحمد": ["یاسوج", "دهدشت", "گچساران", "لیکک", "دوگنبدان"],
    "گلستان": ["گرگان", "گنبدکاووس", "علی‌آباد کتول", "آق‌قلا", "بندر ترکمن", "کردکوی", "آزادشهر", "مینودشت", "بندر گز"],
    "گیلان": ["رشت", "انزلی", "لاهیجان", "لنگرود", "آستارا", "تالش", "رودسر", "صومعه‌سرا", "فومن", "رودبار", "آستانه اشرفیه"],
    "لرستان": ["خرم‌آباد", "بروجرد", "دورود", "کوهدشت", "الیگودرز", "نورآباد", "ازنا", "الشتر", "پلدختر"],
    "مازندران": ["ساری", "بابل", "آمل", "قائم‌شهر", "بابلسر", "تنکابن", "نوشهر", "چالوس", "رامسر", "بهشهر", "نکا", "محمودآباد", "فریدونکنار"],
    "مرکزی": ["اراک", "ساوه", "خمین", "محلات", "دلیجان", "شازند", "تفرش", "آشتیان"],
    "هرمزگان": ["بندرعباس", "قشم", "میناب", "بندر لنگه", "کیش", "رودان", "جاسک", "حاجی‌آباد", "بستک", "پارسیان"],
    "همدان": ["همدان", "ملایر", "نهاوند", "تویسرکان", "اسدآباد", "کبودرآهنگ", "رزن", "بهار"],
    "یزد": ["یزد", "میبد", "اردکان", "بافق", "ابرکوه", "مهریز", "تفت", "اشکذر"],
}

PROVINCES = sorted(CITIES.keys())


def _codes(items) -> set[str]:
    return {c for c, _ in items}


VEHICLE_TYPE_CODES = _codes(VEHICLE_TYPES)
BODY_TYPE_CODES = _codes(BODY_TYPES)
CARGO_TYPE_CODES = _codes(CARGO_TYPES)
AREA_TYPE_CODES = _codes(AREA_TYPES)
LEGAL_TYPE_CODES = _codes(LEGAL_TYPES)
POSITION_CODES = _codes(REPRESENTATIVE_POSITIONS)
COUNTRY_CODES = _codes(COUNTRIES)
PERMIT_TYPE_CODES = {p["code"] for p in PERMIT_TYPES}


def city_in_province(province: str, city: str) -> bool:
    return city in CITIES.get(province, [])


def _opts(items):
    return [{"code": c, "label": l} for c, l in items]


def public_catalog() -> dict:
    """Payload of GET /api/logistics/public/reference."""
    return {
        "legal_types": _opts(LEGAL_TYPES),
        "vehicle_types": _opts(VEHICLE_TYPES),
        "body_types": _opts(BODY_TYPES),
        "cargo_types": _opts(CARGO_TYPES),
        "area_types": _opts(AREA_TYPES),
        "representative_positions": _opts(REPRESENTATIVE_POSITIONS),
        "countries": _opts(COUNTRIES),
        "permit_types": PERMIT_TYPES,
        "provinces": [{"name": p, "cities": CITIES[p]} for p in PROVINCES],
    }
