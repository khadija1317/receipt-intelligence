from src.repair import repair_token


def tok(text, no_sep=False):
    return {"text": text, "conf": 1.0, "no_separator": no_sep}


def test_clean_amount_untouched():
    r = repair_token(tok("60.000"))
    assert r["status"] == "ok" and r["value"] == 60000 and r["repairs"] == []


def test_validation0_total():
    r = repair_token(tok("45_500"))
    assert r["status"] == "repaired" and r["value"] == 45500


def test_separator_on_both_halves():
    assert repair_token(tok("17_,000"))["value"] == 17000


def test_validation80_paren_separator_and_letters():
    r = repair_token(tok("25)0oo"))
    assert r["value"] == 25000 and r["letters"] == ["o", "o"]


def test_idr_join_without_separator_is_repaired():
    r = repair_token(tok("2800o", no_sep=True))
    assert r["status"] == "repaired" and r["value"] == 28000


def test_validation22_apostrophe_separator_and_letters():
    assert repair_token(tok("308'OOD"))["value"] == 308000


def test_leading_quote_is_stripped():
    assert repair_token(tok("'20,000"))["value"] == 20000


def test_q_is_low_trust():
    r = repair_token(tok("18Q00"))
    assert r["value"] == 18000 and r["low_trust"] is True


def test_validation7_extra_digit_goes_to_review():
    r = repair_token(tok("59,5005"))
    assert r["status"] == "review" and r["value"] is None


def test_words_are_never_repaired():
    for text in ["Cod", "Total:", "Sate", "OCD", "(0)"]:
        assert repair_token(tok(text))["status"] == "not_amount"


def test_tnd_letter_repair_is_allowed_but_marked():
    r = repair_token(tok("23.O00"), "TND")
    assert r["status"] == "repaired" and r["value"] == 23


def test_tnd_join_without_separator_never_silent():
    for text in ["2800o", "12500"]:
        r = repair_token(tok(text, no_sep=True), "TND")
        assert r["status"] == "review" and r["value"] is None


def test_tnd_garbled_separator_never_silent():
    r = repair_token(tok("12_500"), "TND")
    assert r["status"] == "review" and r["value"] is None