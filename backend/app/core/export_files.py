"""Excel (.xlsx) and Word (.docx) files for the list exports (customers, suppliers, logistics, sales).

The libraries are imported lazily so the API still starts if they are not installed yet; the export
endpoints then answer with a clear 501 instead.
"""
import re
from io import BytesIO

from flask import send_file

from app.utils.exceptions import ConflictError

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_EXPORT_ROWS = 10_000
PAGE = 500

_FORMULA_START = re.compile(r"^[=+\-@\t\r]")


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "بله" if value else "خیر"
    return str(value)


def _safe(value):
    """Numbers stay numbers; text that a spreadsheet could read as a formula is neutralised."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    text = _text(value)
    return f"'{text}" if _FORMULA_START.match(text) else text


def build_xlsx(title: str, headers: list[str], rows: list[list]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.sheet_view.rightToLeft = True
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="F3F4F6")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in rows:
        ws.append([_safe(v) for v in row])
    for idx, header in enumerate(headers, start=1):
        longest = max([len(_text(header))] + [len(_text(r[idx - 1])) for r in rows[:200]])
        ws.column_dimensions[get_column_letter(idx)].width = min(max(12, longest + 2), 48)
    ws.freeze_panes = "A2"
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def build_docx(title: str, headers: list[str], rows: list[list]) -> bytes:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width

    def rtl(paragraph):
        pPr = paragraph._p.get_or_add_pPr()
        pPr.append(OxmlElement("w:bidi"))
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    heading = doc.add_paragraph()
    run = heading.add_run(title)
    run.bold = True
    run.font.size = Pt(14)
    rtl(heading)

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    tbl_pr = table._tbl.tblPr
    tbl_pr.append(OxmlElement("w:bidiVisual"))  # columns run right-to-left
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(_text(h))
        r.bold = True
        r.font.size = Pt(8)
        rtl(cell.paragraphs[0])
        shading = OxmlElement("w:shd")
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:fill"), "F3F4F6")
        cell._tc.get_or_add_tcPr().append(shading)
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(_text(v))
            r.font.size = Pt(8)
            rtl(cells[i].paragraphs[0])
    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def send_export(fmt: str, *, title: str, filename: str, headers: list[str], rows: list[list]):
    """A download response in the requested format ('xlsx' | 'docx')."""
    fmt = (fmt or "xlsx").lower()
    if fmt not in ("xlsx", "docx"):
        raise ConflictError("Unsupported export format. Use xlsx or docx.")
    try:
        data = build_xlsx(title, headers, rows) if fmt == "xlsx" else build_docx(title, headers, rows)
    except ImportError as exc:  # library missing on the server
        raise ConflictError(f"Export needs the server package 'openpyxl' / 'python-docx': {exc}") from exc
    return send_file(
        BytesIO(data), mimetype=XLSX_MIME if fmt == "xlsx" else DOCX_MIME, as_attachment=True,
        download_name=f"{filename}.{fmt}",
    )


def collect_pages(fetch_page) -> list:
    """Runs `fetch_page(page, per_page) -> (items, total)` until everything (up to MAX_EXPORT_ROWS) is read."""
    out: list = []
    page = 1
    while len(out) < MAX_EXPORT_ROWS:
        items, total = fetch_page(page, PAGE)
        out.extend(items)
        if not items or len(out) >= total:
            break
        page += 1
    return out[:MAX_EXPORT_ROWS]
