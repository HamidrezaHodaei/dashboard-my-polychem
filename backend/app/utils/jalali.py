"""
Pure-Python Jalali (Shamsi) calendar helpers + "today in Tehran".

Used by recurring tasks so that "monthly" / "yearly" mean Persian months and
years (e.g. the 1st of every Farvardin), not Gregorian ones. No third-party
dependency. Conversion follows the widely used jalaali algorithm; tests round-
trip every day of 1380-1430 and check known anchor dates.
"""
from datetime import date, datetime, timedelta, timezone

# Iran abolished DST in 2022: Tehran is a fixed UTC+03:30 today. ZoneInfo is
# preferred (history-aware); the fixed offset is the fallback when the OS has no tz database.
try:  # pragma: no cover - depends on the host
    from zoneinfo import ZoneInfo
    TEHRAN = ZoneInfo("Asia/Tehran")
except Exception:  # pragma: no cover
    TEHRAN = timezone(timedelta(hours=3, minutes=30))


def tehran_now() -> datetime:
    return datetime.now(TEHRAN)


def tehran_today() -> date:
    return tehran_now().date()


def to_tehran(dt: datetime) -> datetime:
    """A naive datetime is taken as UTC (how the DB stores timestamps)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TEHRAN)


_G_D_M = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + _G_D_M[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    jy += 1595
    days = (
        -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd
        + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    )
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    sal_a = (0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def to_jalali(d: date) -> tuple[int, int, int]:
    return gregorian_to_jalali(d.year, d.month, d.day)


def from_jalali(jy: int, jm: int, jd: int) -> date:
    return date(*jalali_to_gregorian(jy, jm, jd))


def is_jalali_leap(jy: int) -> bool:
    # 30 Esfand only exists in a leap year: converting there and back must land on the same day
    return gregorian_to_jalali(*jalali_to_gregorian(jy, 12, 30)) == (jy, 12, 30)


def jalali_month_length(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def add_jalali_months(d: date, months: int, day: int | None = None) -> date:
    """Same Jalali day-of-month N months later; a day past the end of the target
    month (e.g. 31 Shahrivar -> Mehr) is clamped to that month's last day.
    `day` = the day to aim for instead of d's own (lets a series that was clamped once
    return to its real day, e.g. the 31st, in the next 31-day month)."""
    jy, jm, jd = to_jalali(d)
    total = jy * 12 + (jm - 1) + months
    ny, nm = divmod(total, 12)
    nm += 1
    return from_jalali(ny, nm, min(day or jd, jalali_month_length(ny, nm)))


def add_jalali_years(d: date, years: int, day: int | None = None) -> date:
    return add_jalali_months(d, years * 12, day)



# ---------------------------------------------------------------------
# User-supplied date parsing (filters, forms, spreadsheet import)
# ---------------------------------------------------------------------
_DIGIT_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_SEPARATORS = str.maketrans({"-": "/", ".": "/", "\u066b": "/", "\u200c": None, "\u200f": None, "\u200e": None})


def parse_date_input(value) -> date:
    """Any date a client may send -> a Gregorian `date`.

    Accepted: `date`/`datetime`, `YYYY/MM/DD`, `YYYY-MM-DD`, `YYYY.MM.DD`, ISO datetimes
    (`2026-11-06T10:00:00Z`), with Persian/Arabic digits, and non-padded parts (`1405/9/5`).
    The calendar is decided by the year: < 1700 is Jalali (Shamsi), otherwise Gregorian, so a
    Jalali value is converted exactly (never the old `year - 621` guess). Impossible dates raise
    ValueError.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip().translate(_DIGIT_TABLE)
    if not text:
        raise ValueError("empty date")
    text = text.split("T")[0].split(" ")[0].translate(_SEPARATORS)
    parts = text.split("/")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"unrecognised date {value!r}")
    a, b, c = (int(p) for p in parts)
    # Normalise day/month/year order: the year is the 3-4 digit part.
    if len(parts[0]) >= 3:
        y, m, d = a, b, c
    elif len(parts[2]) >= 3:
        y, m, d = c, b, a
    else:
        raise ValueError(f"unrecognised date {value!r}")
    if not 1 <= m <= 12 or d < 1:
        raise ValueError(f"impossible date {value!r}")
    if y < 1700:
        if y < 1 or d > jalali_month_length(y, m):
            raise ValueError(f"impossible date {value!r}")
        return from_jalali(y, m, d)
    return date(y, m, d)  # raises ValueError itself for e.g. 31 June


def format_jalali(d: date | None) -> str | None:
    """`date` -> `YYYY/MM/DD` (Jalali, zero padded) -- the format the panel shows."""
    if d is None:
        return None
    jy, jm, jd = to_jalali(d)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def jalali_month_range(jy: int, jm: int) -> tuple[date, date]:
    """First and last Gregorian day of a Jalali month."""
    return from_jalali(jy, jm, 1), from_jalali(jy, jm, jalali_month_length(jy, jm))


def jalali_year_range(jy: int) -> tuple[date, date]:
    return from_jalali(jy, 1, 1), from_jalali(jy, 12, jalali_month_length(jy, 12))

