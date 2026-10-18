import re

from src.merge import SEPS, ZEROISH, squash
from src.normalize import CURRENCY_DECIMALS, parse_amount

ZERO_MAP = str.maketrans({c: "0" for c in ZEROISH})
PREFIX = re.compile(r"^(Rp\.?|TND|DT)")
DIGITS = "0123456789"
ALLOWED = set(DIGITS) | set(ZEROISH) | set(SEPS)
SEP_RUN = re.compile(r"(?<=\d)[" + re.escape(SEPS) + r"]+(?=\d)")


def _clean_run(match):
    """A run of separator characters between two digits -> one separator.
    Keep the first real '.' or ',' if there is one, otherwise use ','."""
    legit = [c for c in match.group(0) if c in ".,"]
    return legit[0] if legit else ","


def repair_token(token, currency="IDR"):
    raw = token["text"]
    result = {
        "raw": raw, "value": None, "status": "not_amount",
        "repairs": [], "letters": [], "low_trust": False,
        "reason": "", "conf": token.get("conf"),
    }
    decimals = CURRENCY_DECIMALS[currency]

    # 1. TND: a join with no separator is never fixed silently.
    if token.get("no_separator") and decimals > 0:
        result.update(status="review", reason="pieces joined with no separator (TND)")
        return result

    # 2. Direct parse: if the normalizer accepts it, leave it alone.
    try:
        result["value"] = parse_amount(raw, currency)
        result["status"] = "ok"
        return result
    except ValueError:
        pass

    # 3. Shape gate: only amount-shaped tokens may be repaired.
    body = PREFIX.sub("", squash(raw), count=1)
    sign = ""
    if body.startswith("-"):
        sign, body = "-", body[1:]
    if not any(c in DIGITS for c in body) or any(c not in ALLOWED for c in body):
        return result

    repairs = []

    # 4. Stray quotes at the ends.
    stripped = body.strip("'")
    if stripped != body:
        repairs.append("stripped stray quote")
        body = stripped

    # 5. Zero-like letters -> 0.
    letters = [c for c in body if c in ZEROISH]
    if letters:
        body = body.translate(ZERO_MAP)
        repairs.append("zero-like letters -> 0")
    result["letters"] = letters
    result["low_trust"] = "Q" in letters

    # 6. Garbled separators between digit groups.
    cleaned = SEP_RUN.sub(_clean_run, body)
    if cleaned != body:
        if decimals > 0:
            result.update(status="review", repairs=repairs,
                          reason="garbled separator (TND: no silent fix)")
            return result
        repairs.append("garbled separator -> grouping comma")
        body = cleaned

    # 7. Parse the repaired text.
    try:
        result["value"] = parse_amount(sign + body, currency)
    except ValueError as err:
        result.update(status="review", repairs=repairs, reason=f"normalizer refused: {err}")
        return result

    result["repairs"] = repairs
    result["status"] = "repaired" if repairs else "ok"
    return result