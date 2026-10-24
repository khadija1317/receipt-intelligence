from decimal import Decimal

import pytest

from src.extract_rules import _adjacent_total, extract_receipt


def _line(text, label="", amounts=(), kind=None):
    return {"label": label, "kind": kind, "text": text, "amounts": list(amounts)}


def _amt(raw, value):
    return {"value": Decimal(value), "raw": raw, "status": "ok", "conf": 0.99,
            "low_trust": False}


def test_above_amount_is_used_for_a_keyword_only_total_line():
    parsed = [
        _line("Lemon Tea 25.000", "Lemon Tea", [_amt("25.000", "25000")]),
        _line("25.000", "", [_amt("25.000", "25000")]),
        _line("TOTAL", "TOTAL", kind="total"),
        _line("CASH 30.000", "CASH", [_amt("30.000", "30000")]),
    ]
    field = _adjacent_total(parsed, "above")
    assert field["value"] == "25000"
    assert field["adjacent"] == "above"
    assert field["line"] == "25.000 | TOTAL"


def test_below_is_only_used_in_both_mode():
    parsed = [
        _line("TOTAL", "TOTAL", kind="total"),
        _line("20,000", "", [_amt("20,000", "20000")]),
        _line("CASH 30,000", "CASH", [_amt("30,000", "30000")]),
    ]
    assert _adjacent_total(parsed, "above") is None
    field = _adjacent_total(parsed, "both")
    assert field["value"] == "20000"
    assert field["adjacent"] == "below"
    assert field["line"] == "TOTAL | 20,000"


def test_two_amount_only_neighbours_means_review_in_both_mode():
    parsed = [
        _line("1,818", "", [_amt("1,818", "1818")]),
        _line("TOTAL", "TOTAL", kind="total"),
        _line("20,000", "", [_amt("20,000", "20000")]),
    ]
    field = _adjacent_total(parsed, "both")
    assert field["value"] is None
    assert field["status"] == "review"
    assert field["adjacent"] == "ambiguous"
    assert _adjacent_total(parsed, "above")["value"] == "1818"


def test_neighbour_with_a_name_or_two_amounts_is_not_used():
    named = [
        _line("Lemon Tea 25.000", "Lemon Tea", [_amt("25.000", "25000")]),
        _line("TOTAL", "TOTAL", kind="total"),
    ]
    assert _adjacent_total(named, "both") is None
    two = [
        _line("1 25.000", "", [_amt("1", "1"), _amt("25.000", "25000")]),
        _line("TOTAL", "TOTAL", kind="total"),
    ]
    assert _adjacent_total(two, "both") is None


def test_keyword_line_that_has_an_amount_is_not_touched():
    parsed = [
        _line("25.000", "", [_amt("25.000", "25000")]),
        _line("TOTAL 100,000", "TOTAL", [_amt("100,000", "100000")], kind="total"),
    ]
    assert _adjacent_total(parsed, "both") is None


def _rows(texts):
    """Made-up receipt: one OCR piece per row, rows far apart."""
    pieces = []
    for i, text in enumerate(texts):
        y = 100 + 80 * i
        x1 = 100 + 18 * len(text)
        pieces.append({"box": [[100, y], [x1, y], [x1, y + 30], [100, y + 30]],
                       "text": text, "conf": 0.99})
    return pieces


ROWS = ["Lemon Tea (L) 25.000", "25.000", "TOTAL", "CASH 30.000", "CHANGED 5.000"]


def test_default_behaviour_is_v2():
    assert extract_receipt(_rows(ROWS), "IDR")["total"] is None
    assert extract_receipt(_rows(ROWS), "IDR", adjacent="off")["total"] is None


def test_v3_fills_in_the_total_from_the_line_above():
    result = extract_receipt(_rows(ROWS), "IDR", adjacent="above")
    assert result["total"]["value"] == "25000"
    assert result["total"]["line"] == "25.000 | TOTAL"
    assert result["subtotal"] is None


def test_v3_never_overrides_a_total_that_v2_found():
    rows = ["10.000", "TOTAL", "TOTAL 25.000"]
    result = extract_receipt(_rows(rows), "IDR", adjacent="both")
    assert result["total"]["value"] == "25000"
    assert "adjacent" not in result["total"]


def test_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        extract_receipt(_rows(ROWS), "IDR", adjacent="sideways")
