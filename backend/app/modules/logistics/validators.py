"""
Pure (framework-free) validators/normalizers for the logistics wizard.

Kept free of Flask/SQLAlchemy/Pydantic imports so they can be unit-tested
in isolation and reused by schemas.py. Every function accepts Persian /
Arabic-Indic digits and returns Latin digits.
"""
import re

_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_AR_TO_FA = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_ZWNJ = "\u200c"


def to_latin_digits(value: str) -> str:
    return value.translate(_DIGIT_MAP)


def clean_text(value, *, max_len: int | None = None) -> str | None:
    """Trim, collapse whitespace, unify Arabic ي/ك to Persian ی/ک; blank -> None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Value must be text.")
    out = " ".join(value.translate(_AR_TO_FA).split()).strip()
    if not out:
        return None
    if max_len is not None and len(out) > max_len:
        raise ValueError(f"Value is too long (max {max_len} characters).")
    return out


def _digits_only(value: str) -> str:
    return to_latin_digits(value).replace(" ", "").replace("-", "")


def clean_national_code(value) -> str | None:
    """کد ملی: 10 digits + official check digit. Blank -> None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("National code must be text.")
    v = _digits_only(value)
    if not v:
        return None
    if not (v.isascii() and v.isdigit() and len(v) == 10):
        raise ValueError("National code must be exactly 10 digits.")
    if len(set(v)) == 1:
        raise ValueError("National code is not valid.")
    total = sum(int(v[i]) * (10 - i) for i in range(9))
    r = total % 11
    check = r if r < 2 else 11 - r
    if check != int(v[9]):
        raise ValueError("National code is not valid.")
    return v


def clean_legal_national_id(value) -> str | None:
    """شناسه ملی شخص حقوقی: 11 digits + official check digit. Blank -> None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Legal national ID must be text.")
    v = _digits_only(value)
    if not v:
        return None
    if not (v.isascii() and v.isdigit() and len(v) == 11):
        raise ValueError("Legal national ID must be exactly 11 digits.")
    if len(set(v)) == 1 or int(v[3:9]) == 0:
        raise ValueError("Legal national ID is not valid.")
    d = int(v[9]) + 2
    coeffs = (29, 27, 23, 19, 17, 29, 27, 23, 19, 17)
    total = sum((int(v[i]) + d) * coeffs[i] for i in range(10))
    r = total % 11
    if r == 10:
        r = 0
    if r != int(v[10]):
        raise ValueError("Legal national ID is not valid.")
    return v


def clean_mobile(value) -> str | None:
    """Iranian mobile -> canonical 09XXXXXXXXX. Accepts +98 / 0098 / 98 / 9XXXXXXXXX."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Mobile number must be text.")
    v = _digits_only(value).replace("+", "")
    if not v:
        return None
    if v.startswith("0098"):
        v = "0" + v[4:]
    elif v.startswith("98") and len(v) == 12:
        v = "0" + v[2:]
    elif len(v) == 10 and v.startswith("9"):
        v = "0" + v
    if not re.fullmatch(r"09\d{9}", v):
        raise ValueError("Mobile number must look like 09123456789.")
    return v


def clean_landline(value) -> str | None:
    """Iranian landline with area code: 0 + 10 digits, not starting 09 (e.g. 02122334455)."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Phone number must be text.")
    v = _digits_only(value).replace("+", "")
    if not v:
        return None
    if v.startswith("0098"):
        v = "0" + v[4:]
    elif v.startswith("98") and len(v) == 12:
        v = "0" + v[2:]
    if not re.fullmatch(r"0[1-8]\d{9}", v):
        raise ValueError("Landline must include the area code, e.g. 02122334455.")
    return v


def clean_mobile_or_landline(value) -> str | None:
    """Alternate phone for drivers: either a mobile or a landline."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return clean_mobile(value)
    except ValueError:
        return clean_landline(value)
