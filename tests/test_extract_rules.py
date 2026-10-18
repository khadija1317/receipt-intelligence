from decimal import Decimal

from src.extract_rules import extract_receipt


def piece(text, x_left, x_right, y, h, conf=1.0):
    top, bottom = y - h / 2, y + h / 2
    return {"box": [[x_left, top], [x_right, top], [x_right, bottom], [x_left, bottom]],
            "text": text, "conf": conf}


def test_validation0_total_and_item():
    pieces = [piece("REAL GANACHE", 201, 375, 570, 36), piece("16,500", 577, 665, 570, 36),
              piece("TOTAL", 198, 351, 714, 64), piece("45_", 495, 565, 713, 64),
              piece("500", 573, 669, 713, 64),
              piece("CASH", 201, 269, 760, 36), piece("50,000", 579, 671, 760, 36)]
    r = extract_receipt(pieces)
    assert Decimal(r["total"]["value"]) == 45500 and r["total"]["status"] == "repaired"
    assert [m["nm"] for m in r["menu"]] == ["REAL GANACHE"]  # CASH is not an item


def test_subtotal_service_tax_total_are_told_apart():
    pieces = [piece("SubTotal:", 208, 320, 508, 32), piece("63,636", 412, 492, 508, 32),
              piece("Service", 208, 320, 540, 32), piece("7,725", 412, 492, 540, 32),
              piece("PB1", 208, 320, 573, 32), piece("11,073", 412, 492, 573, 32),
              piece("Total:", 198, 302, 652, 56), piece("59,500", 408, 510, 652, 56)]
    r = extract_receipt(pieces)
    assert Decimal(r["subtotal"]["value"]) == 63636
    assert Decimal(r["service"]["value"]) == 7725
    assert Decimal(r["tax"]["value"]) == 11073
    assert Decimal(r["total"]["value"]) == 59500


def test_total_item_and_total_qty_are_not_the_total():
    pieces = [piece("Total item", 100, 250, 300, 32), piece("3", 400, 420, 300, 32),
              piece("Total Qty", 100, 250, 340, 32), piece("3", 400, 420, 340, 32)]
    r = extract_receipt(pieces)
    assert r["total"] is None and r["menu"] == []


def test_total_tax_included_goes_to_tax_not_total():
    pieces = [piece("Total Tax Included", 100, 330, 300, 32), piece("15,000", 400, 480, 300, 32)]
    r = extract_receipt(pieces)
    assert r["total"] is None and Decimal(r["tax"]["value"]) == 15000


def test_item_with_count_and_garbled_price():
    pieces = [piece("1", 219, 235, 794, 24), piece("Sate", 258, 360, 794, 36),
              piece("Padang", 378, 527, 794, 36), piece("25)", 639, 691, 794, 36),
              piece("0oo", 709, 787, 794, 36),
              piece("Total", 210, 385, 880, 72), piece("25.OOO", 633, 789, 880, 72)]
    r = extract_receipt(pieces)
    item = r["menu"][0]
    assert item["nm"] == "Sate Padang" and item["cnt"] == "1"
    assert Decimal(item["price"]["value"]) == 25000 and item["price"]["status"] == "repaired"


def test_missing_total_keyword_without_amount_is_noted():
    r = extract_receipt([piece("Total", 100, 200, 300, 32)])
    assert r["total"] is None and r["notes"]["keyword_without_amount"] == ["total"]


def test_unreadable_total_is_kept_as_review_not_skipped():
    pieces = [piece("Total:", 198, 302, 652, 56), piece("59,5005", 408, 510, 652, 56)]
    r = extract_receipt(pieces)
    assert r["total"]["value"] is None and r["total"]["status"] == "review"