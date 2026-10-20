import re

from src.merge import merge_receipt
from src.repair import repair_token

TOTAL_EXCLUDE = ("sub", "item", "qty", "tax")
TAX_WORDS = ("tax", "pb1", "pbi", "pajak", "ppn")
SERVICE_WORDS = ("serv", "charge")
NOT_ITEM = ("total", "qty", "item", "cash", "change")
KINDS = ("subtotal", "total", "tax", "service")


def _norm(label):
    """'Sub Total:' -> 'subtotal'"""
    return re.sub(r"[^a-z0-9]", "", label.lower())


def classify(label):
    norm = _norm(label)
    if "subtotal" in norm:
        return "subtotal"
    if "total" in norm and not any(w in norm for w in TOTAL_EXCLUDE):
        return "total"
    if any(w in norm for w in TAX_WORDS):
        return "tax"
    if any(w in norm for w in SERVICE_WORDS):
        return "service"
    return None

def _edit_distance(a, b):
    """How many single-letter edits turn a into b (add, remove or change a letter)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1,                 # remove a letter
                           cur[j - 1] + 1,              # add a letter
                           prev[j - 1] + (ca != cb)))   # change a letter
        prev = cur
    return prev[-1]


def classify_fuzzy(label):
    """Second chance for lines classify() missed: 'Tota]' -> 'total'.
    One edit allowed, words of 4+ letters only, digit 0 read as the letter o."""
    full = _norm(label)
    for word in label.split():
        w = re.sub(r"[^a-z0-9]", "", word.lower().replace("0", "o"))
        if len(w) < 4:
            continue
        if _edit_distance(w, "subtotal") <= 1:
            return "subtotal"
        if _edit_distance(w, "total") <= 1 and not any(x in full for x in TOTAL_EXCLUDE):
            return "total"
    return None


def classify_any(label):
    """v1 rule first. The fuzzy rule only runs when v1 found nothing."""
    return classify(label) or classify_fuzzy(label)


def line_parts(line, currency):
    """One merged line -> (label text, list of amount results, left to right)."""
    words, amounts = [], []
    for token in line["tokens"]:
        result = repair_token(token, currency)
        if result["status"] != "not_amount":
            amounts.append(result)
            continue
        parts = token["text"].split()
        if len(parts) > 1:  # 'TOTAL 60.000' in one piece: try only the last word
            last = repair_token({**token, "text": parts[-1], "no_separator": False}, currency)
            if last["status"] != "not_amount":
                words.append(" ".join(parts[:-1]))
                amounts.append(last)
                continue
        words.append(token["text"])
    return " ".join(words), amounts


def field_of(result):
    value = result["value"]
    return {
        "value": None if value is None else str(value),
        "raw": result["raw"],
        "status": result["status"],      # ok / repaired / review
        "conf": result["conf"],
        "low_trust": result["low_trust"],
    }


def extract_receipt(pieces, currency="IDR", fuzzy=True):
    parsed = []
    for line in merge_receipt(pieces):
        label, amounts = line_parts(line, currency)
        parsed.append({"label": label,
                       "kind": classify_any(label) if fuzzy else classify(label),
                       "amounts": amounts, "text": line["text"]})

    notes = {"keyword_without_amount": [], "orphan_amount_lines": 0}
    first_summary = None
    for n, p in enumerate(parsed):
        if p["kind"]:
            if first_summary is None:
                first_summary = n
            if not p["amounts"]:
                notes["keyword_without_amount"].append(p["kind"])

    def pick(kind):
        candidates = [p for p in parsed if p["kind"] == kind and p["amounts"]]
        if not candidates:
            return None
        chosen = candidates[-1]  # the lowest such line on the receipt
        field = field_of(chosen["amounts"][-1])  # rightmost amount
        field["line"] = chosen["text"]
        field["n_candidates"] = len(candidates)
        return field

    end = first_summary if first_summary is not None else len(parsed)
    menu = []
    for p in parsed[:end]:
        if not p["amounts"] or any(w in _norm(p["label"]) for w in NOT_ITEM):
            continue
        if not re.search(r"[A-Za-z]", p["label"]):
            notes["orphan_amount_lines"] += 1  # an amount with no name beside it
            continue
        cnt = None
        first_raw = p["amounts"][0]["raw"].strip()
        if len(p["amounts"]) >= 2 and re.fullmatch(r"\d{1,2}", first_raw):
            cnt = first_raw
        menu.append({"nm": p["label"], "cnt": cnt,
                     "price": field_of(p["amounts"][-1])})

    result = {"menu": menu, "notes": notes}
    for kind in KINDS:
        result[kind] = pick(kind)
    return result