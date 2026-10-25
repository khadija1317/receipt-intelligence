"""Validator: look at ONE extraction record and say which checks fail.

It never sees the image. It sees the record (and the OCR text, if given).
Every flag has a short code and a plain-words reason.
"""
from decimal import Decimal

from src.normalize import parse_amount

FIELDS = ("subtotal", "total", "tax", "service")
CASH_WORDS = ("cash", "tunai")
CHANGE_WORDS = ("change", "kembali")
# A total below this is suspicious. Only IDR is set (a guess); other currencies skip the check.
TINY_TOTAL = {"IDR": Decimal(1000)}
# Checks that can notice a plausible WRONG number (not just "nothing readable here").
VALUE_CODES = {"TOTAL_VS_BASE", "ITEMS_VS_SUBTOTAL", "CASH_CHANGE_TOTAL", "TINY_TOTAL",
               "NUMBER_NOT_IN_TEXT", "EVIDENCE_NOT_IN_TEXT", "TOTAL_WORD_MISSING"}
# Decision 6b: a receipt goes to the review queue when a number on it cannot be trusted.
# The other flags (NO_ITEMS, ZERO_PRICE, ITEM_UNREADABLE, REPAIRED) stay on the record as notes.
QUEUE_CODES = VALUE_CODES | {"MISSING_TOTAL", "FIELD_REVIEW"}


def _value(field):
    """A field dict -> Decimal, or None if it is missing or has no readable value."""
    if not field or field.get("value") is None:
        return None
    try:
        return Decimal(str(field["value"]))
    except ArithmeticError:
        return None


def _flag(code, reason):
    return {"code": code, "reason": reason}


def _squash(text):
    """Lower-case and collapse all whitespace, so spacing differences do not matter."""
    return " ".join(str(text).lower().split())


def find_cash_change(text, currency="IDR"):
    """Look for ONE line with a cash word and an amount, and ONE with a change word and an amount.

    A line is a label followed by an amount at the end. A line with both a cash word and a
    change word (a fused line) is skipped, because we cannot tell which amount is which.
    """
    found = {"cash": None, "change": None}
    for line in text.split("\n"):
        tokens = [t for t in line.split("  ") if t.strip()]
        if len(tokens) < 2:
            continue
        label = " ".join(tokens[:-1]).lower()
        try:
            amount = parse_amount(tokens[-1].strip(), currency)
        except ValueError:
            continue
        has_cash = any(w in label for w in CASH_WORDS)
        has_change = any(w in label for w in CHANGE_WORDS)
        if has_cash == has_change:  # neither word, or both words
            continue
        key = "cash" if has_cash else "change"
        if found[key] is None:
            found[key] = amount
    return found


def all_amounts(text, currency="IDR"):
    """Every piece of the text that parses as an amount, as a set of Decimals."""
    out = set()
    for line in text.split("\n"):
        for token in line.split("  "):
            try:
                out.add(parse_amount(token.strip(), currency))
            except ValueError:
                pass
    return out


def measure_gaps(record, cash_change=None):
    """The SIZE of each disagreement. None means 'this check could not run'."""
    menu = record.get("menu") or []
    sub = _value(record.get("subtotal"))
    tot = _value(record.get("total"))
    tax = _value(record.get("tax")) or Decimal(0)
    svc = _value(record.get("service")) or Decimal(0)
    prices = [_value(m.get("price")) for m in menu]
    item_sum = None
    if menu and all(p is not None for p in prices):
        item_sum = sum(prices, Decimal(0))

    gaps = {"items_vs_subtotal": None, "total_vs_base": None, "cash_change": None}
    if item_sum is not None and sub is not None:
        gaps["items_vs_subtotal"] = abs(item_sum - sub)
    base = sub if sub is not None else item_sum
    if base is not None and tot is not None:
        # Accept BOTH receipt styles: tax added on top, or tax already inside the total.
        gaps["total_vs_base"] = min(abs(base + tax + svc - tot), abs(base - tot))
    if cash_change and tot is not None:
        cash, change = cash_change["cash"], cash_change["change"]
        if cash is not None and change is not None:
            gaps["cash_change"] = abs(cash - change - tot)
    return gaps


def validate(record, *, tolerance, text=None, currency="IDR", grounding=False):
    """Run every check on one record. tolerance is REQUIRED (a Decimal): no silent default."""
    flags = []
    menu = record.get("menu") or []
    total = _value(record.get("total"))

    # 1. Missing things
    if total is None:
        flags.append(_flag("MISSING_TOTAL", "no readable total on this receipt"))
    if not menu:
        flags.append(_flag("NO_ITEMS", "no items were extracted"))

    # 2. Fields that are present but not clean
    for key in FIELDS:
        field = record.get(key)
        if not field or (key == "total" and total is None):
            continue
        if field.get("status") == "review" or field.get("value") is None:
            flags.append(_flag("FIELD_REVIEW",
                               f"{key} could not be read cleanly (status {field.get('status')})"))
        elif field.get("status") == "repaired":
            flags.append(_flag("REPAIRED", f"{key} was repaired from an OCR misread"))

    # 3. Item prices
    unreadable = zero = repaired = 0
    for m in menu:
        price = m.get("price") or {}
        v = _value(price)
        if v is None:
            unreadable += 1
        elif v == 0:
            zero += 1
        if price.get("status") == "repaired":
            repaired += 1
    if unreadable:
        flags.append(_flag("ITEM_UNREADABLE", f"{unreadable} item(s) have no readable price"))
    if zero:
        flags.append(_flag("ZERO_PRICE", f"{zero} item(s) have price 0"))
    if repaired:
        flags.append(_flag("REPAIRED", f"{repaired} item price(s) were repaired"))

    # 4. Tiny total
    tiny = TINY_TOTAL.get(currency)
    if total is not None and tiny is not None and total < tiny:
        flags.append(_flag("TINY_TOTAL", f"total {total:,} is below {tiny:,}"))

    # 5. Arithmetic and payment
    cash_change = find_cash_change(text, currency) if text else None
    gaps = measure_gaps(record, cash_change)
    if gaps["items_vs_subtotal"] is not None and gaps["items_vs_subtotal"] > tolerance:
        flags.append(_flag("ITEMS_VS_SUBTOTAL",
                           f"item prices and subtotal differ by {gaps['items_vs_subtotal']:,}"))
    if gaps["total_vs_base"] is not None and gaps["total_vs_base"] > tolerance:
        flags.append(_flag("TOTAL_VS_BASE",
                           f"total does not match the subtotal (or item sum), with or without "
                           f"tax and service added; the closest match is still {gaps['total_vs_base']:,} off"))
    if gaps["cash_change"] is not None and gaps["cash_change"] > tolerance:
        flags.append(_flag("CASH_CHANGE_TOTAL",
                           f"cash minus change differs from the total by {gaps['cash_change']:,}"))

    # 6. Grounding (LLM arm only): is the answer really in the text it was given?
    if grounding and text:
        amounts = all_amounts(text, currency)
        squashed = _squash(text)
        for key in FIELDS:
            field = record.get(key)
            v = _value(field)
            if v is None:
                continue
            if v not in amounts:
                flags.append(_flag("NUMBER_NOT_IN_TEXT", f"{key} {v:,} appears nowhere in the OCR text"))
            evidence = field.get("line")
            if not evidence or _squash(evidence) not in squashed:
                flags.append(_flag("EVIDENCE_NOT_IN_TEXT", f"evidence line for {key} is not in the OCR text"))
            if key == "total" and evidence and "total" not in evidence.lower():
                flags.append(_flag("TOTAL_WORD_MISSING", f"evidence for total has no 'total' word: {evidence!r}"))

    evaluated = [k for k, v in gaps.items() if v is not None]
    if grounding and text:
        evaluated.append("grounding")
    queue = [x for x in flags if x["code"] in QUEUE_CODES]
    return {"flagged": bool(flags), "review": bool(queue), "flags": flags,
            "gaps": gaps, "evaluated": evaluated}
