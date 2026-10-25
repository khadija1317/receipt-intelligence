"""Tests for src/validate.py. Records are MADE UP; some copy the shape of real
validation receipts (2, 16, 70, 94), noted in comments."""
from decimal import Decimal

import pytest

from src.validate import find_cash_change, validate


def f(value, status="ok", line=None):
    """A field dict like the extractors write."""
    return {"value": None if value is None else str(value), "status": status, "line": line}


def item(price, status="ok"):
    return {"nm": "x", "cnt": None, "price": f(price, status)}


def rec(prices=(), subtotal=None, total=None, tax=None, service=None):
    return {"menu": [item(p) for p in prices],
            "subtotal": subtotal, "total": total, "tax": tax, "service": service}


def codes(out):
    return {x["code"] for x in out["flags"]}


T1 = Decimal(1)


def test_clean_record_not_flagged():
    # shape of real val 70 on Paddle text: everything adds up
    r = rec([69000, 19000, 15000], f(103000), f(121798), f(11073), f(7725))
    out = validate(r, tolerance=T1)
    assert out["flagged"] is False
    assert out["gaps"]["items_vs_subtotal"] == 0
    assert out["gaps"]["total_vs_base"] == 0


def test_rounding_gap_of_one():
    # shape of real val 2: 18,181 + 1,818 = 19,999 against a total of 20,000
    r = rec([18181], f(18181), f(20000), f(1818))
    assert validate(r, tolerance=T1)["flagged"] is False
    assert "TOTAL_VS_BASE" in codes(validate(r, tolerance=Decimal(0)))


def test_val16_shape_flags_and_cash_not_evaluable():
    # cash amount sits on the TOTAL line; the CHANGE line has no amount
    text = "0  20,000\nTT  20000\nTOTAL  100,000\nCASH  80,000\nCHANGE"
    r = rec([20000], total=f(100000, line="TOTAL  100,000"))
    out = validate(r, tolerance=T1, text=text)
    assert codes(out) == {"TOTAL_VS_BASE"}
    assert out["gaps"]["total_vs_base"] == Decimal(80000)
    assert out["gaps"]["cash_change"] is None
    assert "cash_change" not in out["evaluated"]


def test_no_items_no_subtotal_means_not_evaluable():
    out = validate(rec([], total=f(10000)), tolerance=T1)
    assert codes(out) == {"NO_ITEMS"}
    assert out["gaps"]["total_vs_base"] is None
    assert out["evaluated"] == []


def test_unreadable_item_price_is_not_a_pass():
    r = rec([], f(10000), f(10000))
    r["menu"] = [item(None, "review")]
    out = validate(r, tolerance=T1)
    assert "ITEM_UNREADABLE" in codes(out)
    assert out["gaps"]["items_vs_subtotal"] is None
    assert "items_vs_subtotal" not in out["evaluated"]


def _val94():
    # shape of real val 94 (LLM arm); the text is made up from that shape
    r = rec([69000], f(0, line="SUB TOTAL  0"), f(80100, line="TADA EGIFT  80.100"),
            service=f(7280, line="SERVICE  7.280"))
    text = "Emily Scampi  69.000\nSUB TOTAL  0\nSERVICE  7.280\nTADA EGIFT  80.100"
    return r, text


def test_val94_total_word_missing():
    r, text = _val94()
    out = validate(r, tolerance=T1, text=text, grounding=True)
    assert {"ITEMS_VS_SUBTOTAL", "TOTAL_VS_BASE", "TOTAL_WORD_MISSING"} <= codes(out)
    assert "EVIDENCE_NOT_IN_TEXT" not in codes(out)


def test_grounding_off_for_rules_arm():
    r, text = _val94()
    out = validate(r, tolerance=T1, text=text, grounding=False)
    assert "TOTAL_WORD_MISSING" not in codes(out)


def test_invented_evidence_flags():
    r = rec([45000], total=f(45000, line="TOTAL  45,000"))
    out = validate(r, tolerance=T1, text="TOTAL  50,000", grounding=True)
    assert {"NUMBER_NOT_IN_TEXT", "EVIDENCE_NOT_IN_TEXT"} <= codes(out)


def test_missing_total_flags():
    assert "MISSING_TOTAL" in codes(validate(rec([5000]), tolerance=T1))


def test_absent_optional_fields_do_not_flag():
    out = validate(rec([10000], total=f(10000)), tolerance=T1)
    assert out["flagged"] is False


def test_review_status_flags():
    r = rec([10000], total=f(10000), tax=f(None, "review"))
    assert "FIELD_REVIEW" in codes(validate(r, tolerance=T1))


def test_repaired_status_flags():
    r = rec([10000], total=f(10000), tax=f(1818, "repaired"))
    assert "REPAIRED" in codes(validate(r, tolerance=T1))


def test_zero_price_flags():
    assert "ZERO_PRICE" in codes(validate(rec([0]), tolerance=T1))


def test_tiny_total_idr():
    out = validate(rec([500], total=f(500)), tolerance=T1, currency="IDR")
    assert "TINY_TOTAL" in codes(out)


def test_tiny_total_not_checked_for_dinar():
    out = validate(rec(["4.500"], total=f("4.500")), tolerance=T1, currency="TND")
    assert "TINY_TOTAL" not in codes(out)
    assert out["flagged"] is False


def test_tax_inclusive_receipt_passes():
    r = rec([100000], f(100000), f(100000), f(10000))
    assert validate(r, tolerance=T1)["flagged"] is False


def test_items_short_of_subtotal_flags():
    # shape of EasyOCR val 70: 67,000 read for 69,000; the totals still add up
    r = rec([67000, 19000, 15000], f(103000), f(121798), f(11073), f(7725))
    assert codes(validate(r, tolerance=T1)) == {"ITEMS_VS_SUBTOTAL"}


def test_find_cash_change_normal():
    got = find_cash_change("Total:  20,000\nCASH  100,000\nCHANGE  80,000")
    assert got == {"cash": Decimal(100000), "change": Decimal(80000)}
    got = find_cash_change("TUNAI  50,000\nKEMBALI  8,000")
    assert got == {"cash": Decimal(50000), "change": Decimal(8000)}


def test_find_cash_change_skips_fused_line():
    # shape of real val 47: one line holding both words
    got = find_cash_change("Pay Cash 50,000 Total. Change  :8,000")
    assert got == {"cash": None, "change": None}


def test_cash_minus_change_mismatch_flags():
    r = rec([18181], f(18181), f(20000), f(1818))
    out = validate(r, tolerance=T1, text="CASH  100,000\nCHANGE  70,000")
    assert codes(out) == {"CASH_CHANGE_TOTAL"}


def test_tolerance_is_required():
    with pytest.raises(TypeError):
        validate(rec([1000], total=f(1000)))


def test_gaps_do_not_depend_on_tolerance():
    r = rec([18181], f(18181), f(20000), f(1818))
    assert (validate(r, tolerance=Decimal(0))["gaps"]
            == validate(r, tolerance=Decimal(1000))["gaps"])


def test_weak_flags_do_not_enter_review_queue():
    out = validate(rec([], total=f(10000)), tolerance=T1)
    assert codes(out) == {"NO_ITEMS"}
    assert out["flagged"] is True
    assert out["review"] is False


def test_value_flag_enters_review_queue():
    r = rec([20000], total=f(100000))
    assert validate(r, tolerance=T1)["review"] is True


def test_missing_total_enters_review_queue():
    assert validate(rec([5000]), tolerance=T1)["review"] is True
