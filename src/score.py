"""Scorer for the extractor. Pure functions: no file reading here."""
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from src.normalize import parse_amount

FIELDS = ("total", "subtotal", "tax", "service")

# Where each field lives inside the label (gt_parse).
LABEL_KEYS = {
    "total": ("total", "total_price"),
    "subtotal": ("sub_total", "subtotal_price"),
    "tax": ("sub_total", "tax_price"),
    "service": ("sub_total", "service_price"),
}


def as_list(menu):
    """CORD stores one item as a dict and several as a list. Always return a list."""
    if menu is None:
        return []
    if isinstance(menu, dict):
        return [menu]
    return list(menu)


def label_fields(gt_parse, currency="IDR"):
    """Label -> ({field: Decimal}, [fields whose label text the normalizer refuses])."""
    values, unparseable = {}, []
    for name, (group, key) in LABEL_KEYS.items():
        block = gt_parse.get(group)
        if not isinstance(block, dict) or key not in block:
            continue  # the label has no such field: it will not be scored
        try:
            values[name] = parse_amount(str(block[key]), currency)
        except ValueError:
            unparseable.append(name)  # e.g. "(0)"
    return values, unparseable


def to_count(text):
    """'2' -> 2, 'x2' -> 2, '1x' -> 1, anything else -> None."""
    if text is None:
        return None
    m = re.fullmatch(r"\s*[xX]?\s*(\d+)\s*[xX]?\s*", str(text))
    return int(m.group(1)) if m else None


def label_items(gt_parse, currency="IDR"):
    """Top-level label items -> ([{nm, cnt, price}], tally of skipped items)."""
    items = []
    skipped = {"no_price": 0, "unparseable": 0}
    for item in as_list(gt_parse.get("menu")):
        if not isinstance(item, dict) or item.get("price") in (None, ""):
            skipped["no_price"] += 1
            continue
        try:
            price = parse_amount(str(item["price"]), currency)
        except ValueError:
            skipped["unparseable"] += 1
            continue
        items.append({"nm": item.get("nm"), "cnt": to_count(item.get("cnt")),
                      "price": price})
    return items, skipped

def to_decimal(field):
    """An extractor field (dict with 'value' as text) -> Decimal, or None."""
    if not field or field.get("value") is None:
        return None
    try:
        return Decimal(str(field["value"]))
    except InvalidOperation:
        return None


def score_field(label_value, field):
    got = to_decimal(field)
    if label_value is None:
        return "not_scored" if got is None else "extra"
    if got is None:
        return "no_answer"
    return "correct" if got == label_value else "wrong"

def score_items(label_list, extracted_menu):
    """Decision 1a: match by price only; each label price can be used once."""
    unused = list(label_list)
    matched = wrong = unreadable = 0
    name_sim_sum, name_sim_n = 0.0, 0
    count_checked = count_agree = 0
    for item in extracted_menu:
        got = to_decimal(item.get("price"))
        if got is None:
            unreadable += 1  # no price to compare: not counted as returned (2a)
            continue
        hit = next((k for k, lab in enumerate(unused) if lab["price"] == got), None)
        if hit is None:
            wrong += 1  # wrong extra: a price with no partner
            continue
        lab = unused.pop(hit)  # this label price is now used up
        matched += 1
        if lab["nm"] and item.get("nm"):
            a, b = str(lab["nm"]).lower(), str(item["nm"]).lower()
            name_sim_sum += SequenceMatcher(None, a, b).ratio()
            name_sim_n += 1
        if lab["cnt"] is not None:
            count_checked += 1
            if to_count(item.get("cnt")) == lab["cnt"]:
                count_agree += 1
    return {
        "matched": matched,
        "returned": matched + wrong,
        "label_count": len(label_list),
        "unreadable": unreadable,
        "name_sim_sum": name_sim_sum, "name_sim_n": name_sim_n,
        "count_checked": count_checked, "count_agree": count_agree,
    }

def score_receipt(gt_parse, extracted, currency="IDR"):
    label_vals, unparseable = label_fields(gt_parse, currency)
    fields = {}
    for name in FIELDS:
        field = extracted.get(name)
        if name in unparseable:
            outcome = "unparseable_label"
        else:
            outcome = score_field(label_vals.get(name), field)
        status = field.get("status", "missing") if field else "missing"
        fields[name] = {"outcome": outcome, "status": status}

    label_list, skipped = label_items(gt_parse, currency)
    items = score_items(label_list, extracted.get("menu") or [])

    fields_ok = all(f["outcome"] in ("correct", "not_scored", "extra", "unparseable_label")
                    for f in fields.values())
    items_ok = (items["matched"] == items["label_count"] == items["returned"]
                and items["unreadable"] == 0)
    return {"fields": fields, "items": items,
            "label_items_skipped": skipped, "exact": fields_ok and items_ok}


def ratio(a, b):
    return None if b == 0 else a / b


def summarize(results):
    out = {"receipts": len(results), "fields": {}}
    for name in FIELDS:
        tally = Counter(r["fields"][name]["outcome"] for r in results)
        correct, wrong, no_answer = tally["correct"], tally["wrong"], tally["no_answer"]
        p = ratio(correct, correct + wrong)
        rec = ratio(correct, correct + wrong + no_answer)
        if p is None or rec is None:
            f1 = None
        elif p + rec == 0:
            f1 = 0.0
        else:
            f1 = 2 * p * rec / (p + rec)
        review_but_answered = sum(
            1 for r in results
            if r["fields"][name]["status"] == "review"
            and r["fields"][name]["outcome"] in ("correct", "wrong"))
        out["fields"][name] = {
            "correct": correct, "wrong": wrong, "no_answer": no_answer,
            "extra": tally["extra"], "not_scored": tally["not_scored"],
            "unparseable_label": tally["unparseable_label"],
            "review_but_answered": review_but_answered,
            "precision": p, "recall": rec, "f1": f1,
        }

    its = [r["items"] for r in results]
    matched = sum(i["matched"] for i in its)
    returned = sum(i["returned"] for i in its)
    label_count = sum(i["label_count"] for i in its)
    out["items"] = {
        "matched": matched, "returned": returned, "label_count": label_count,
        "unreadable": sum(i["unreadable"] for i in its),
        "precision": ratio(matched, returned),
        "recall": ratio(matched, label_count),
        "name_similarity": ratio(sum(i["name_sim_sum"] for i in its),
                                 sum(i["name_sim_n"] for i in its)),
        "count_agreement": ratio(sum(i["count_agree"] for i in its),
                                 sum(i["count_checked"] for i in its)),
    }
    out["exact"] = sum(1 for r in results if r["exact"])
    out["label_items_skipped"] = {
        k: sum(r["label_items_skipped"][k] for r in results) for k in ("no_price", "unparseable")}
    return out
