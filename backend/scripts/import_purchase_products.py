"""
ONE-TIME bulk import of the purchase product catalog (purchase_products) from an Excel file.

Excel columns (header row, any order): «کد» | «عنوان» | «دسته‌بندی کالا»
    کد               -> purchase_products.code   (kept EXACTLY as text: leading zeros, letters, separators)
    عنوان            -> purchase_products.name
    دسته‌بندی کالا   -> the commodity group, matched by name with the main categories of the supplier bank

Safe by design
    * DRY-RUN by default: nothing is written until you pass --apply.
    * All-or-nothing: one transaction; any error rolls everything back.
    * Re-runnable: rows whose code or name already exists are skipped, never duplicated or overwritten.
    * Every skipped / suspicious row goes to a CSV report next to the script's working directory.

Usage (from the backend project root, with the app's .env / virtualenv):
    python scripts/import_purchase_products.py "کالا2.xlsx"                  # check only
    python scripts/import_purchase_products.py "کالا2.xlsx" --apply          # really import
Options:
    --sheet NAME           sheet to read (default: the first one)
    --create-categories    create commodity groups that do not exist yet (default: such rows are imported WITHOUT a group)
    --user-id N            user recorded as creator (default: none)
    --report-dir DIR       where to write the CSV report (default: current directory)

Text clean-up applied: Arabic ك / ي / ى -> Persian ک / ی, tatweel removed, runs of spaces collapsed, ends trimmed.
Codes are only trimmed (never converted). If Excel stored a code as a NUMBER, leading zeros are already lost in the file:
those rows are flagged in the report so you can check them.
"""
import argparse
import csv
import os
import re
import sys
import unicodedata
from datetime import datetime

CODE_RE = re.compile(r"^[\w\-./\\+#()\[\] ]+$", re.UNICODE)  # keep in sync with app/modules/purchases/catalog.py
NAME_MAX, CODE_MAX = 255, 64
HEADERS = {"code": ("کد", "کدکالا", "code"), "name": ("عنوان", "نام", "نامکالا", "name", "title"),
           "category": ("دستهبندیکالا", "دستهبندی", "گروهکالایی", "گروه", "category")}
_ARABIC = str.maketrans({"ك": "ک", "ي": "ی", "ى": "ی", "ـ": None})


def clean_text(value) -> str:
    return " ".join(str(value).translate(_ARABIC).replace("\xa0", " ").split())


def key_of(text: str) -> str:
    """comparison key: ignores case, spaces and half-spaces (ZWNJ) so «دسته‌بندی» == «دسته بندی»"""
    return clean_text(text).replace("\u200c", "").replace(" ", "").lower()


def dup_key(text: str) -> str:
    """Duplicate-detection key that mirrors how MySQL's *_ci collations compare text.

    The unique index on purchase_products.name / .code is case- AND accent-insensitive and ignores
    zero-width characters, so «آلات» == «الات», «دسته‌بندی» == «دسته‌‌بندی» and any harakat (َ ُ ِ ّ) are
    ignored. Comparing with plain .lower() missed those pairs and the database rejected the insert."""
    t = unicodedata.normalize("NFKD", clean_text(text))
    t = "".join(ch for ch in t if unicodedata.category(ch) not in ("Mn", "Cf"))  # accents/harakat, ZWNJ/ZWJ
    return " ".join(t.casefold().split())


def _find_columns(header_row) -> dict:
    found = {}
    for idx, cell in enumerate(header_row):
        k = key_of(cell) if cell is not None else ""
        for field, names in HEADERS.items():
            if k in names and field not in found:
                found[field] = idx
    return found if {"code", "name"} <= set(found) else {"code": 0, "name": 1, "category": 2}


def read_rows(path: str, sheet: str | None = None) -> list[dict]:
    """Rows of the sheet as {line, code, name, category, flags}. No database access."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    cols = _find_columns(next(it, ()))
    out = []
    for line, row in enumerate(it, start=2):
        def cell(field):
            i = cols.get(field)
            return row[i] if i is not None and i < len(row) else None
        raw_code, raw_name, raw_cat = cell("code"), cell("name"), cell("category")
        if all(v is None or str(v).strip() == "" for v in (raw_code, raw_name, raw_cat)):
            continue  # empty row
        flags = []
        if isinstance(raw_code, (int, float)) and not isinstance(raw_code, bool):
            code = str(int(raw_code)) if float(raw_code).is_integer() else str(raw_code)
            flags.append("کد در اکسل به‌صورت عدد ذخیره شده؛ صفرهای ابتدای آن ممکن است از بین رفته باشد")
        else:
            code = "" if raw_code is None else str(raw_code).strip()
        out.append({"line": line, "code": code, "name": clean_text(raw_name) if raw_name is not None else "",
                    "category": clean_text(raw_cat) if raw_cat is not None else "", "flags": flags})
    return out


def plan(rows: list[dict], existing_names: set[str], existing_codes: set[str], category_keys: set[str]):
    """Decide per row: import or skip (with a reason). Pure function -> (to_import, skipped, warnings)."""
    seen_names = {dup_key(n): "system" for n in existing_names}
    seen_codes = {dup_key(c): "system" for c in existing_codes}
    to_import, skipped, warnings = [], [], []

    def where(origin) -> str:
        return "از قبل در سیستم وجود دارد" if origin == "system" else f"در ردیف {origin} همین فایل آمده است"

    for r in rows:
        name, code = r["name"], r["code"]
        nk, ck = dup_key(name), (dup_key(code) if code else "")
        why = None
        if not name:
            why = "عنوان خالی است"
        elif len(name) > NAME_MAX:
            why = f"عنوان بیش از {NAME_MAX} نویسه است"
        elif code and len(code) > CODE_MAX:
            why = f"کد بیش از {CODE_MAX} نویسه است"
        elif code and not CODE_RE.match(code):
            why = "کد نویسهٔ غیرمجاز دارد (فقط حرف، عدد و - _ . / \\ + # ( ) [ ] و فاصله)"
        elif code and ck in seen_codes:
            why = f"کد تکراری است ({where(seen_codes[ck])})"
        elif nk in seen_names:
            why = f"نام تکراری است ({where(seen_names[nk])})"
        if why:
            skipped.append({**r, "reason": why})
            continue
        seen_names[nk] = r["line"]
        if code:
            seen_codes[ck] = r["line"]
        for f in r["flags"]:
            warnings.append({**r, "reason": f})
        if r["category"] and key_of(r["category"]) not in category_keys:
            warnings.append({**r, "reason": "گروه کالایی در سیستم وجود ندارد"})
        if not code:
            warnings.append({**r, "reason": "کد ندارد"})
        to_import.append(r)
    return to_import, skipped, warnings


def insert_rows(session, build, rows: list[dict], batch_size: int = 500):
    """Insert `rows` (build(row) -> ORM object) inside the caller's transaction.
    Fast path: batches. If a batch hits a unique-key conflict that dup_key() did not foresee, only THAT
    batch is retried row by row (each in a SAVEPOINT) and the conflicting rows are returned as
    skipped instead of aborting the whole import. Returns (inserted_rows, conflicts)."""
    from sqlalchemy.exc import IntegrityError

    inserted, conflicts = [], []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        try:
            with session.begin_nested():
                session.add_all([build(r) for r in chunk])
                session.flush()
            inserted.extend(chunk)
        except IntegrityError:
            for r in chunk:
                try:
                    with session.begin_nested():
                        session.add(build(r))
                        session.flush()
                    inserted.append(r)
                except IntegrityError as exc:
                    detail = str(getattr(exc, "orig", exc))[:160]
                    conflicts.append({**r, "reason": f"تداخل با کلید یکتای دیتابیس (کد یا نام معادل موجود است): {detail}"})
    return inserted, conflicts


def write_report(path: str, skipped: list[dict], warnings: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["نوع", "ردیف در اکسل", "کد", "عنوان", "دسته‌بندی", "توضیح"])
        for kind, items in (("ردشده", skipped), ("هشدار", warnings)):
            for r in items:
                w.writerow([kind, r["line"], r["code"], r["name"], r["category"], r["reason"]])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx")
    ap.add_argument("--apply", action="store_true", help="write to the database (default: dry-run)")
    ap.add_argument("--sheet")
    ap.add_argument("--create-categories", action="store_true")
    ap.add_argument("--user-id", type=int)
    ap.add_argument("--report-dir", default=".")
    args = ap.parse_args()

    rows = read_rows(args.xlsx, args.sheet)
    print(f"ردیف‌های خوانده‌شده از فایل: {len(rows)}")

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv

    load_dotenv()
    from sqlalchemy import select, inspect

    from app import create_app
    from app.core.audit_logs.services import write_audit_log
    from app.extensions import db
    from app.modules.purchases.models import PurchaseProduct
    from app.modules.suppliers.models import SupplierCategory

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        if not inspect(db.engine).has_table("purchase_products"):
            print("جدول purchase_products وجود ندارد؛ ابتدا `flask db upgrade` را اجرا کنید.")
            return 1
        if args.user_id is not None:
            from app.core.users.models import User

            if db.session.get(User, args.user_id) is None:
                print(f"کاربر {args.user_id} پیدا نشد.")
                return 1
        cats = {key_of(c.name): c for c in db.session.scalars(select(SupplierCategory).where(SupplierCategory.parent_id.is_(None)))}
        names = set(db.session.scalars(select(PurchaseProduct.name)))
        codes = {c for c in db.session.scalars(select(PurchaseProduct.code)) if c}

        to_import, skipped, warnings = plan(rows, names, codes, set(cats))
        missing = sorted({r["category"] for r in to_import if r["category"] and key_of(r["category"]) not in cats})

        report = os.path.join(args.report_dir, f"purchase_products_import_{datetime.now():%Y%m%d_%H%M%S}.csv")
        write_report(report, skipped, warnings)
        print(f"قابل ثبت: {len(to_import)} | ردشده: {len(skipped)} | هشدار: {len(warnings)}")
        print(f"گزارش: {report}")
        if missing:
            print("گروه‌های کالایی ناموجود در سیستم:")
            for m in missing:
                print("   -", m)
            print("   →", "ساخته می‌شوند (--create-categories)" if args.create_categories else "این کالاها بدون گروه ثبت می‌شوند (یا از --create-categories استفاده کنید)")
        if not args.apply:
            print("\nاین فقط بررسی بود و چیزی ثبت نشد. برای ثبت واقعی دوباره با --apply اجرا کنید.")
            return 0

        try:
            if args.create_categories:
                order = db.session.scalar(select(db.func.coalesce(db.func.max(SupplierCategory.sort_order), 0))) or 0
                for m in missing:
                    order += 1
                    c = SupplierCategory(name=m, sort_order=order, is_active=True)
                    db.session.add(c)
                    db.session.flush()
                    cats[key_of(m)] = c
            def build(r):
                cat = cats.get(key_of(r["category"])) if r["category"] else None
                return PurchaseProduct(name=r["name"], code=r["code"] or None, category_id=cat.id if cat else None,
                                       is_active=True, created_by_user_id=args.user_id)

            inserted, conflicts = insert_rows(db.session, build, to_import)
            if conflicts:
                skipped.extend(conflicts)
                write_report(report, skipped, warnings)  # rewrite the report including the late conflicts
                print(f"⚠ {len(conflicts)} ردیف به‌دلیل تداخل کلید یکتا در دیتابیس ثبت نشد (در گزارش آمده است).")
            write_audit_log(user_id=args.user_id, action="bulk_import", module="procurement", entity_type="purchase_product",
                            entity_id=None, metadata={"file": os.path.basename(args.xlsx), "imported": len(inserted),
                                                      "skipped": len(skipped)})
            db.session.commit()
        except Exception:
            db.session.rollback()
            print("خطا رخ داد؛ هیچ چیزی ثبت نشد (همه‌چیز برگشت داده شد).")
            raise
        print(f"\n✔ {len(inserted)} کالا ثبت شد.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
