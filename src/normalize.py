import re
from decimal import Decimal

CURRENCY_DECIMALS = {"IDR": 0, "TND": 3}

_PREFIX = re.compile(r"^(rp\.?|tnd|dt)", re.IGNORECASE)
_SUFFIX = re.compile(r"(tnd|dt)$", re.IGNORECASE)


class AmountParseError(ValueError):
    pass


def _strip_grouping(part: str, original: str) -> str:
    """Remove grouping separators from the integer part, validating the groups."""
    seps = {c for c in part if c in ".,"}
    if not seps:
        return part
    if len(seps) != 1:
        raise AmountParseError(f"mixed separators in {original!r}")
    g = seps.pop()
    groups = part.split(g)
    if not (1 <= len(groups[0]) <= 3 and all(len(x) == 3 for x in groups[1:])):
        raise AmountParseError(f"bad digit grouping in {original!r}")
    return "".join(groups)


def parse_amount(text, currency: str) -> Decimal:
    """Parse a printed money amount into an exact Decimal, using the currency's
    number of decimal digits to interpret '.' and ','. Raises AmountParseError
    (a ValueError) on anything it can't read confidently."""
    if currency not in CURRENCY_DECIMALS:
        raise ValueError(f"unknown currency: {currency!r}")
    decimals = CURRENCY_DECIMALS[currency]
    if not isinstance(text, str):
        raise AmountParseError(f"expected a string, got {type(text).__name__}")

    s = _PREFIX.sub("", text.strip().replace("\u2212", "-")).strip()
    negative = s.startswith("-")
    if negative:
        s = s[1:]
    s = _SUFFIX.sub("", s.strip())
    s = re.sub(r"[\s\u00a0\u202f]", "", s)  # spaces used as thousands marks

    if not re.fullmatch(r"[\d.,]+", s) or not re.search(r"\d", s):
        raise AmountParseError(f"not an amount: {text!r}")

    seps = [i for i, c in enumerate(s) if c in ".,"]
    if not seps:
        value = Decimal(s)
    else:
        last = seps[-1]
        sep_char, before, after = s[last], s[:last], s[last + 1:]
        if not before or not (1 <= len(after) <= 3):
            raise AmountParseError(f"cannot place the separator in {text!r}")

        # 1-2 digits after the last separator: always a decimal part.
        # 3 digits: decimal point if the currency has 3 decimals (TND),
        # otherwise a grouping separator (IDR).
        if len(after) < 3 or decimals == 3:
            if sep_char in before:
                raise AmountParseError(f"ambiguous separators in {text!r}")
            value = Decimal(f"{_strip_grouping(before, text)}.{after}")
        else:
            value = Decimal(_strip_grouping(s, text))

    return -value if negative else value