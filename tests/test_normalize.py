from decimal import Decimal
import pytest
from src.normalize import parse_amount

IDR_CASES = [
    ("60.000", 60000),
    ("-60.000", -60000),
    ("91000", 91000),
    ("Rp. 91,000", 91000),
    ("Rp 38.000", 38000),
    ("Rp.118.000", 118000),
    ("Rp 165000.00", 165000),
    ("63,000.00", 63000),
    ("9.500,00", 9500),
    ("1,565,938", 1565938),
    ("Rp 224,908", 224908),
    ("2,352,460", 2352460),
    ("Rp 58000.00", 58000),
    ("Rp. 35.000", 35000),
]

TND_CASES = [
    ("12.500", Decimal("12.5")),
    ("12,500", Decimal("12.5")),   # French-style decimal comma (check on real receipts)
    ("12,50", Decimal("12.5")),
    ("1.234,500", Decimal("1234.5")),
    ("12", 12),
]

GARBAGE = ["abc", "", "   ", "Rp", "-", "12.", "1,2345", "1.234.56", None, 12]


@pytest.mark.parametrize("text,expected", IDR_CASES)
def test_idr(text, expected):
    assert parse_amount(text, "IDR") == Decimal(expected)


@pytest.mark.parametrize("text,expected", TND_CASES)
def test_tnd(text, expected):
    assert parse_amount(text, "TND") == Decimal(expected)


def test_same_digits_opposite_meaning():
    # The trap from the README: same string, values 1000x apart.
    assert parse_amount("12.500", "IDR") == Decimal(12500)
    assert parse_amount("12.500", "TND") == Decimal("12.5")


@pytest.mark.parametrize("text", GARBAGE)
def test_garbage_raises(text):
    with pytest.raises(ValueError):
        parse_amount(text, "IDR")


def test_accounting_parentheses_are_rejected():
    # Deliberate: '(0)' is printed on real receipts (CORD test #17, discount),
    # but we treat it as unreadable rather than guess its sign.
    with pytest.raises(ValueError):
        parse_amount("(0)", "IDR")