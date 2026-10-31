"""Run one receipt through every stage and keep what each stage produced.

OCR runs as a separate process in the paddle venv, so a native crash cannot take the app down.
Everything after OCR runs in this process with the settings of the measured rules/Paddle
pipeline: rules v3 (adjacent="both"), validator tolerance 1, grounding off.
"""
import json
import subprocess
import tempfile
import time
from decimal import Decimal
from pathlib import Path

from src.extract_rules import extract_receipt
from src.geometry import group_rows
from src.llm_extract import render_receipt
from src.merge import merge_receipt
from src.repair import repair_token
from src.validate import QUEUE_CODES, find_cash_change, validate

CURRENCY = "IDR"
TOLERANCE = Decimal(1)  # frozen on Day 7; same value as scripts/run_validate.py
ADJACENT = "both"       # rules v3, the arm in the results tables
OCR_TIMEOUT_SECONDS = 120

REPO_ROOT = Path(__file__).resolve().parents[1]
PADDLE_PYTHON = REPO_ROOT / ".venv-paddle" / "Scripts" / "python.exe"


def _fail(message, started=None):
    wall = 0.0 if started is None else round(time.time() - started, 2)
    return {"ok": False, "message": message, "wall_seconds": wall}


def run_ocr(image_path, timeout=OCR_TIMEOUT_SECONDS):
    """OCR one image in a separate process. Never raises: returns {"ok": ...} either way."""
    if not PADDLE_PYTHON.exists():
        return _fail("OCR failed: the OCR environment (.venv-paddle) was not found.")
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "ocr.json"
        command = [str(PADDLE_PYTHON), "-m", "scripts.ocr_one_image",
                   "--image", str(Path(image_path).resolve()), "--out", str(out)]
        try:
            proc = subprocess.run(command, cwd=REPO_ROOT, timeout=timeout,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return _fail(f"OCR failed: it took longer than {timeout} seconds and was stopped.", started)
        except OSError as err:
            return _fail(f"OCR failed: the OCR process could not start ({err}).", started)
        wall = round(time.time() - started, 2)
        if proc.returncode == 3:
            return _fail("OCR failed: the engine could not read this image at any size.", started)
        if proc.returncode != 0 or not out.exists():
            return _fail("OCR failed: the OCR engine crashed on this image.", started)
        record = json.loads(out.read_text(encoding="utf-8"))
    return {"ok": True, "record": record, "wall_seconds": wall}


def _timed(fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, round(time.perf_counter() - t0, 4)


def merge_view(pieces, lines):
    """Per row: the raw pieces with confidence, and the merged text with joins in {braces}."""
    rows = []
    for row, line in zip(group_rows(pieces), lines):
        rows.append({
            "raw": "  ".join(f"{b['text']} [{b['conf']:.2f}]" for b in row),
            "merged": " ".join("{" + t["text"] + "}" if t["joined"] else t["text"]
                               for t in line["tokens"]),
            "joined": any(t["joined"] for t in line["tokens"]),
        })
    return rows


def repair_view(lines):
    """Every amount-shaped token on the receipt, as the repair step saw it."""
    rows = []
    for n, line in enumerate(lines, 1):
        for token in line["tokens"]:
            result = repair_token(token, CURRENCY)
            if result["status"] == "not_amount":
                parts = token["text"].split()
                if len(parts) > 1:  # 'TOTAL 60.000' in one piece: same last-word trial as the extractor
                    last = repair_token({**token, "text": parts[-1], "no_separator": False}, CURRENCY)
                    if last["status"] != "not_amount":
                        result = last
            if result["status"] == "not_amount":
                continue
            value = result["value"]
            rows.append({
                "line": n,
                "raw": result["raw"],
                "status": result["status"],
                "value": None if value is None else f"{value:,}",
                "what_changed": "; ".join(result["repairs"]) or result["reason"],
            })
    return rows


def _has(field):
    return bool(field) and field.get("value") is not None


def arithmetic_checks(record, validation, text):
    """The three arithmetic checks: did each run, how big is its gap, and if not, why not."""
    gaps = validation["gaps"]
    menu = record.get("menu") or []
    total_ok = _has(record.get("total"))

    why_items = None
    if gaps["items_vs_subtotal"] is None:
        if not menu:
            why_items = "no items were extracted"
        elif not all(_has(m.get("price")) for m in menu):
            why_items = "an item price could not be read"
        else:
            why_items = "no readable subtotal"

    why_base = None
    if gaps["total_vs_base"] is None:
        why_base = ("no readable total" if not total_ok
                    else "no readable subtotal and no readable item prices")

    why_cash = None
    if gaps["cash_change"] is None:
        if not total_ok:
            why_cash = "no readable total"
        else:
            found = find_cash_change(text, CURRENCY) if text else {"cash": None, "change": None}
            if found["cash"] is None and found["change"] is None:
                why_cash = "neither a cash line nor a change line was found"
            elif found["cash"] is None:
                why_cash = "no cash line found"
            else:
                why_cash = "no change line found"

    def row(name, key, why):
        gap = gaps[key]
        return {"name": name, "ran": gap is not None,
                "gap": None if gap is None else f"{gap:,}", "why_not": why}

    return [row("Items vs subtotal", "items_vs_subtotal", why_items),
            row("Total vs subtotal (or item sum)", "total_vs_base", why_base),
            row("Cash minus change vs total", "cash_change", why_cash)]


def build_verdict(validation, checks):
    queue = [f for f in validation["flags"] if f["code"] in QUEUE_CODES]
    notes = [f for f in validation["flags"] if f["code"] not in QUEUE_CODES]
    return {"state": "review" if queue else "passed",
            "reasons": queue,
            "notes": notes,
            "checks_ran": sum(c["ran"] for c in checks),
            "checks_total": len(checks)}


def run_stages(pieces):
    """Raw OCR pieces -> every stage's output plus seconds per stage."""
    seconds = {}
    lines, seconds["merge"] = _timed(merge_receipt, pieces)
    merged = merge_view(pieces, lines)
    repaired, seconds["repair"] = _timed(repair_view, lines)
    record, seconds["extract"] = _timed(extract_receipt, pieces, CURRENCY, adjacent=ADJACENT)
    text, seconds["render_text"] = _timed(render_receipt, pieces, CURRENCY)
    validation, seconds["validate"] = _timed(
        validate, record, tolerance=TOLERANCE, text=text, currency=CURRENCY, grounding=False)
    checks = arithmetic_checks(record, validation, text)
    return {"merge": merged, "repair": repaired, "record": record, "text": text,
            "validation": validation, "checks": checks,
            "verdict": build_verdict(validation, checks), "seconds": seconds}


EXAMPLES_DIR = REPO_ROOT / "demo_examples"


def load_example(stem, folder=None):
    """One shipped example: its image path and its saved OCR result, or None if a file is missing.
    The OCR did not run for it, so the result is marked source="cache"."""
    folder = Path(folder) if folder else EXAMPLES_DIR
    image = folder / f"{stem}.jpg"
    ocr_file = folder / f"{stem}_ocr.json"
    if not image.exists() or not ocr_file.exists():
        return None
    record = json.loads(ocr_file.read_text(encoding="utf-8"))
    return {"image_path": str(image),
            "ocr": {"ok": True, "record": record, "wall_seconds": None, "source": "cache"}}
