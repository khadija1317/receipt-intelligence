from src.extract_rules import classify, classify_any, classify_fuzzy


def test_misspellings_seen_on_validation_are_caught():
    for label in ["Tota]", "Tota", "Totah", "Tota/  Bayar", "3T0TAL", "TQTAL", "6 Tatal", "6 Tota E"]:
        assert classify_fuzzy(label) == "total", label
    assert classify_fuzzy("Subtota]") == "subtotal"


def test_short_or_unrelated_words_do_not_match():
    for label in ["0T", "TT", "Tot", "Cash", "Tunai", "Nasi Goreng", "Seaweed Chicken", "10 |AL"]:
        assert classify_fuzzy(label) is None, label


def test_exclusion_words_still_block_total():
    assert classify_fuzzy("Tota] Qty") is None
    assert classify_fuzzy("Tota] Item") is None


def test_v1_classification_is_never_overridden():
    assert classify_any("Total") == classify("Total") == "total"
    assert classify_any("Sub Total:") == classify("Sub Total:") == "subtotal"
    assert classify_any("Tax") == classify("Tax") == "tax"
    assert classify_any("Service Charge") == "service"


def test_fuzzy_only_runs_when_v1_found_nothing():
    assert classify("Tota]") is None
    assert classify_any("Tota]") == "total"