from src.merge import merge_receipt


def piece(text, x_left, x_right, y, h, conf=1.0):
    top, bottom = y - h / 2, y + h / 2
    return {
        "box": [[x_left, top], [x_right, top], [x_right, bottom], [x_left, bottom]],
        "text": text,
        "conf": conf,
    }


def tokens(pieces):
    """Texts of all tokens, one list per line."""
    return [[t["text"] for t in line["tokens"]] for line in merge_receipt(pieces)]


def test_validation0_total_joins():
    pieces = [piece("TOTAL", 198, 351, 714, 64),
              piece("45_", 495, 565, 713, 64),
              piece("500", 573, 669, 713, 64)]
    assert tokens(pieces) == [["TOTAL", "45_500"]]


def test_separator_on_both_halves_joins_with_overlap():
    pieces = [piece("GRAIN CROQUE  MONSIEUR", 247, 513, 668, 32),
              piece("17 _", 588, 624, 666, 32),
              piece(",000", 613, 671, 666, 32)]
    assert tokens(pieces)[0][-1] == "17_,000"


def test_validation80_gap_at_half_a_text_height_joins_and_qty_stays_apart():
    pieces = [piece("1", 219, 235, 794, 24),
              piece("Sate", 258, 360, 794, 36),
              piece("Padang", 378, 527, 794, 36),
              piece("25)", 639, 691, 794, 36),
              piece("0oo", 709, 787, 794, 36)]
    assert tokens(pieces) == [["1", "Sate", "Padang", "25)0oo"]]


def test_two_complete_amounts_are_not_glued():
    pieces = [piece("216,000", 400, 470, 500, 30),
              piece("432,000", 480, 550, 500, 30)]
    assert tokens(pieces) == [["216,000", "432,000"]]


def test_shape_matches_but_gap_too_wide():
    pieces = [piece("45_", 495, 565, 713, 64),
              piece("500", 800, 900, 713, 64)]
    assert tokens(pieces) == [["45_", "500"]]


def test_validation3_unit_price_does_not_join_line_total():
    pieces = [piece("0oo", 1366, 1484, 1814, 76),
              piece("28", 1597, 1689, 1811, 76),
              piece("Ooo", 1702, 1823, 1813, 76)]
    assert tokens(pieces) == [["0oo", "28Ooo"]]


def test_no_separator_flag():
    with_sep = merge_receipt([piece("45_", 495, 565, 713, 64),
                              piece("500", 573, 669, 713, 64)])
    without = merge_receipt([piece("28", 1597, 1689, 2224, 79),
                             piece("00o", 1699, 1823, 2224, 79)])
    assert with_sep[0]["tokens"][0]["no_separator"] is False
    assert without[0]["tokens"][0]["no_separator"] is True


def test_list_order_does_not_matter():
    pieces = [piece("500", 589, 677, 739, 60),
              piece("42_", 517, 581, 741, 60),
              piece("TOTAL", 244, 383, 742, 60)]
    assert tokens(pieces) == [["TOTAL", "42_500"]]


def test_item_rows_stay_separate():
    pieces = [piece("12,500", 587, 667, 607, 36),
              piece("13,000", 588, 668, 636, 32)]
    assert len(merge_receipt(pieces)) == 2


def test_merged_confidence_is_the_lower_one():
    pieces = [piece("45_", 495, 565, 713, 64, conf=1.0),
              piece("500", 573, 669, 713, 64, conf=0.4)]
    assert merge_receipt(pieces)[0]["tokens"][0]["conf"] == 0.4