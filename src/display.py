"""Turn the pipeline's output into things a page can show: an HTML banner and plain table rows.

No Gradio in this file, so everything here can be tested without a browser.
Every piece of text that can come from a receipt is escaped before it goes into HTML.
"""
from decimal import Decimal
from html import escape

# Measured on the unseen CORD splits (test + holdout B = CORD train 0-399): rules v3 on Paddle text.
# Source: docs/results_notes.md. "Wrong value" means a wrong total, subtotal, tax or service
# value; items are not part of this definition.
MEASURED = {
    "receipts": 500,
    "queued": 218,
    "not_queued": 282,
    "wrong_value": 30,
    "wrong_value_queued": 29,
    "wrong_value_not_queued": 1,
}

ARITHMETIC_CODES = {"TOTAL_VS_BASE", "ITEMS_VS_SUBTOTAL", "CASH_CHANGE_TOTAL"}
RED = "#b42318"
GREEN = "#067647"

FIELD_NAMES = (("total", "Total"), ("subtotal", "Subtotal"), ("tax", "Tax"), ("service", "Service"))
FIELD_HEADERS = ["Field", "Value", "As the OCR printed it", "Status", "Taken from line"]
ITEM_HEADERS = ["Item", "Qty", "Price", "Status"]
MERGE_HEADERS = ["Row", "Raw OCR pieces [confidence]", "After merge ({ } = joined)", "Joined"]
REPAIR_HEADERS = ["Line", "As the OCR printed it", "Status", "Value", "What changed"]
CHECK_HEADERS = ["Check", "Could run", "Gap", "Why not"]
TIMING_HEADERS = ["Stage", "Time", "Note"]

ADJACENT_TEXT = {
    "above": "amount taken from the line above the total word",
    "below": "amount taken from the line below the total word",
    "ambiguous": "an amount above and one below both qualify, so none was chosen",
}


def _fmt(value):
    """'100000' -> '100,000'; None stays None."""
    if value is None:
        return None
    try:
        return f"{Decimal(value):,}"
    except ArithmeticError:
        return str(value)


def _banner(color, title, body):
    return (f'<div style="background:{color};color:#fff;padding:14px 16px;border-radius:8px;">'
            f'<div style="font-size:1.25em;font-weight:700;letter-spacing:0.02em;">{escape(title)}</div>'
            f"{body}</div>")


def _checks_html(verdict, checks):
    lines = []
    for c in checks:
        if c["ran"]:
            lines.append(f'{escape(c["name"])}: ran, gap {escape(str(c["gap"]))}')
        else:
            lines.append(f'{escape(c["name"])}: could not run ({escape(str(c["why_not"]))})')
    items = "".join(f"<li>{line}</li>" for line in lines)
    return (f'<div style="margin-top:10px;">Arithmetic checks that could run: '
            f'<b>{verdict["checks_ran"]} of {verdict["checks_total"]}</b></div>'
            f'<ul style="margin:4px 0 0 18px;font-size:0.9em;">{items}</ul>')


def _notes_html(verdict):
    if not verdict["notes"]:
        return ""
    text = "; ".join(escape(n["reason"]) for n in verdict["notes"])
    return (f'<div style="margin-top:8px;font-size:0.9em;">'
            f"Notes (these do not send a receipt to review): {text}</div>")


def _measured_html(state):
    m = MEASURED
    if state == "review":
        text = (f"On {m['receipts']} CORD receipts the pipeline was not tuned on, "
                f"{m['wrong_value_queued']} of {m['wrong_value']} records with a wrong value were queued, "
                f"and {m['queued']} of {m['receipts']} receipts ({m['queued'] / m['receipts']:.1%}) "
                f"were queued in total.")
    else:
        text = (f"On {m['receipts']} CORD receipts the pipeline was not tuned on, {m['not_queued']} had no "
                f"review flag, and {m['wrong_value_not_queued']} of them had a wrong total, subtotal, tax or "
                f"service value. Items are not checked. Receipts that are not from CORD were not measured.")
    return f'<div style="margin-top:10px;font-size:0.9em;opacity:0.95;">{escape(text)}</div>'


def verdict_html(verdict, checks):
    """The banner at the top of the page."""
    if verdict["state"] == "review":
        reasons = "".join(
            f'<li>{escape(f["reason"])} <small>({escape(f["code"])})</small></li>'
            for f in verdict["reasons"])
        body = f'<ul style="margin:8px 0 0 18px;">{reasons}</ul>'
        if any(f["code"] in ARITHMETIC_CODES for f in verdict["reasons"]):
            body += ('<div style="margin-top:6px;">The validator can say that numbers disagree, '
                     "not which one is wrong.</div>")
        title, color = "SEND TO REVIEW", RED
    else:
        body = ('<div style="margin-top:6px;">No review flag fired. This says what the checks found, '
                "not that the receipt is right.</div>")
        title, color = "PASSED THE CHECKS", GREEN
    body += _checks_html(verdict, checks) + _notes_html(verdict) + _measured_html(verdict["state"])
    return _banner(color, title, body)


def fields_rows(record):
    rows = []
    for key, name in FIELD_NAMES:
        f = record.get(key)
        if not f:
            rows.append([name, "not found", "", "", ""])
            continue
        value = _fmt(f.get("value")) or "unreadable"
        line = f.get("line", "")
        if f.get("adjacent"):
            line = f"{line}  ({ADJACENT_TEXT.get(f['adjacent'], f['adjacent'])})"
        rows.append([name, value, f.get("raw", ""), f.get("status", ""), line])
    return rows


def items_rows(record):
    rows = []
    for m in record.get("menu") or []:
        price = m.get("price") or {}
        rows.append([m.get("nm", ""), m.get("cnt") or "",
                     _fmt(price.get("value")) or "unreadable", price.get("status", "")])
    return rows


def merge_rows(merge):
    return [[n, r["raw"], r["merged"], "yes" if r["joined"] else ""] for n, r in enumerate(merge, 1)]


def repair_rows(repair):
    return [[r["line"], r["raw"], r["status"], r["value"] or "", r["what_changed"]] for r in repair]


def check_rows(checks):
    return [[c["name"], "yes" if c["ran"] else "no", c["gap"] or "", c["why_not"] or ""]
            for c in checks]


def _secs(s):
    return "n/a" if s is None else f"{s:.1f} s"


def _ms(s):
    return f"{s * 1000:.1f} ms"


def timing_rows(stage_seconds, ocr_seconds=None, ocr_load_seconds=None,
                ocr_wall_seconds=None, ocr_source="live"):
    rows = []
    if ocr_source == "cache":
        rows.append(["OCR: predict", _secs(ocr_seconds),
                     "from the cached file; the OCR did not run for this example"])
    else:
        rows.append(["OCR: predict", _secs(ocr_seconds), "Paddle reading the image"])
        rows.append(["OCR: model loading", _secs(ocr_load_seconds),
                     "paid again on every upload (a fresh process each time)"])
        rows.append(["OCR: whole subprocess", _secs(ocr_wall_seconds),
                     "includes starting Python and importing Paddle"])
    notes = (
        ("merge", "Merge", "run once for this page; the extractor runs its own merge"),
        ("repair", "Repair", "run once for this page; the extractor runs its own repair"),
        ("extract", "Extractor (rules v3)", "includes its own merge and repair"),
        ("render_text", "Text for the validator", "merge and repair again, to build the text it reads"),
        ("validate", "Validator", "arithmetic and cash/change checks"),
    )
    for key, name, note in notes:
        rows.append([name, _ms(stage_seconds[key]), note])
    return rows


def failure_html(message):
    """Shown when no verdict exists (no image, OCR failed). It is not a verdict on the receipt."""
    return ('<div style="background:#475467;color:#fff;padding:14px 16px;border-radius:8px;">'
            '<div style="font-size:1.25em;font-weight:700;letter-spacing:0.02em;">NO RESULT</div>'
            f'<div style="margin-top:6px;">{escape(message)}</div>'
            '<div style="margin-top:6px;font-size:0.9em;">This is not a verdict on the receipt. '
            "Nothing was checked.</div></div>")
