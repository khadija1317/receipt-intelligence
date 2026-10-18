import re

from src.geometry import group_rows

JOIN_GAP = 1.0         # decision 2: max gap between two pieces, in text heights
SEPS = "_,.;)'"         # PROVISIONAL (decision 3): characters seen standing in for a separator
ZEROISH = "oOQDCud"     # PROVISIONAL (decision 3): letters seen standing in for a 0

_SEP = re.escape(SEPS)
_LEFT = re.compile(r"^\d{1,3}[" + _SEP + r"]?$")
_RIGHT = re.compile(r"^[" + _SEP + r"]?[\d" + re.escape(ZEROISH) + r"]{3}$")


def squash(text):
    """Remove all whitespace: '17 _' -> '17_'."""
    return "".join(text.split())


def gap_ratio(left, right):
    """Horizontal gap between two pieces, in units of the smaller text height."""
    gap = right["x_left"] - left["x_right"]
    return gap / max(min(left["h"], right["h"]), 1)


def shape_match(left, right):
    """Does this pair LOOK like the two halves of one amount?"""
    return bool(_LEFT.match(squash(left["text"])) and _RIGHT.match(squash(right["text"])))


def _join(left, right):
    text = squash(left["text"]) + squash(right["text"])
    return {
        "text": text,
        "conf": min(left["conf"], right["conf"]),
        "x_left": left["x_left"],
        "x_right": right["x_right"],
        "y_center": (left["y_center"] + right["y_center"]) / 2,
        "h": max(left["h"], right["h"]),
        "joined": True,
        "no_separator": not any(ch in SEPS for ch in text),
    }


def merge_row(row, join_gap=JOIN_GAP):
    """Walk one row left to right, joining shape-matching neighbours that are close enough."""
    tokens = []
    i = 0
    while i < len(row):
        if (i + 1 < len(row)
                and shape_match(row[i], row[i + 1])
                and gap_ratio(row[i], row[i + 1]) <= join_gap):
            tokens.append(_join(row[i], row[i + 1]))
            i += 2
        else:
            tokens.append({**row[i], "joined": False, "no_separator": False})
            i += 1
    return tokens


def merge_receipt(pieces, join_gap=JOIN_GAP):
    """Raw OCR pieces -> list of lines, top to bottom."""
    lines = []
    for row in group_rows(pieces):
        tokens = merge_row(row, join_gap)
        lines.append({
            "y_center": sum(t["y_center"] for t in tokens) / len(tokens),
            "tokens": tokens,
            "text": " ".join(t["text"] for t in tokens),
            "min_conf": min(t["conf"] for t in tokens),
        })
    return lines