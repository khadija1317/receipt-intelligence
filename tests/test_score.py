from decimal import Decimal

from src.score import (as_list, label_fields, label_items, score_field,
                       score_items, score_receipt, summarize)


def amount(v, status="ok"):
    return {"value": v, "status": status}


def item(nm, price, cnt=None):
    return {"nm": nm, "cnt": cnt, "price": amount(price)}


def lab(price, nm="x", cnt=None):
    return {"nm": nm, "cnt": cnt, "price": Decimal(price)}


def test_label_fields_normalizes():
    gt = {"total": {"total_price": "Rp. 45,500"}, "sub_total": {"tax_price": "4.136"}}
    values, unparseable = label_fields(gt)
    assert values == {"total": Decimal("45500"), "tax": Decimal("4136")}
    assert unparseable == []


def test_unparseable_label_is_tallied_not_dropped():
    values, unparseable = label_fields({"sub_total": {"service_price": "(0)"}})
    assert values == {}
    assert unparseable == ["service"]


def test_lone_menu_dict_is_wrapped():
    assert as_list({"nm": "A"}) == [{"nm": "A"}]
    items, skipped = label_items({"menu": {"nm": "A", "cnt": "1", "price": "16,500"}})
    assert len(items) == 1 and items[0]["price"] == Decimal("16500")
    assert skipped == {"no_price": 0, "unparseable": 0}


def test_score_field_outcomes():
    label = Decimal("100")
    assert score_field(label, {"value": "100"}) == "correct"
    assert score_field(label, {"value": "100.00"}) == "correct"
    assert score_field(label, {"value": "90"}) == "wrong"
    assert score_field(label, {"value": None, "status": "review"}) == "no_answer"
    assert score_field(label, None) == "no_answer"
    assert score_field(None, None) == "not_scored"
    assert score_field(None, {"value": "5"}) == "extra"


def test_duplicate_label_price_is_used_once():
    r = score_items([lab("15000"), lab("15000")], [item("a", "15000")])
    assert (r["matched"], r["returned"], r["label_count"]) == (1, 1, 2)
    r = score_items([lab("15000")], [item("a", "15000"), item("b", "15000")])
    assert (r["matched"], r["returned"], r["label_count"]) == (1, 2, 1)


def test_one_digit_misread_like_val70():
    labels = [lab("69000"), lab("19000"), lab("15000")]
    extracted = [item("a", "67000"), item("b", "19000"), item("c", "15000")]
    r = score_items(labels, extracted)
    assert (r["matched"], r["returned"], r["label_count"]) == (2, 3, 3)


def test_zero_price_modifiers_hurt_precision_not_recall():
    extracted = [item("a", "16500"), item("m1", "0"), item("m2", "0"), item("m3", "0")]
    r = score_items([lab("16500")], extracted)
    assert (r["matched"], r["returned"], r["label_count"]) == (1, 4, 1)


def test_unreadable_item_price_is_not_returned():
    r = score_items([lab("16500")], [{"nm": "a", "cnt": None, "price": amount(None, "review")}])
    assert (r["matched"], r["returned"], r["unreadable"]) == (0, 0, 1)


def test_name_and_count_side_numbers():
    r = score_items([lab("8000", nm="Es Teh", cnt=2)], [item("Es Tah", "8000", cnt="2")])
    assert r["count_checked"] == 1 and r["count_agree"] == 1
    assert 0.8 < r["name_sim_sum"] / r["name_sim_n"] < 1


def test_exact_match_and_wrong_total():
    gt = {"total": {"total_price": "45,500"},
          "menu": {"nm": "A", "cnt": "1", "price": "45,500"}}
    good = {"menu": [item("A", "45500", cnt="1")], "total": amount("45500")}
    bad = {"menu": [item("A", "45500", cnt="1")], "total": amount("45000")}
    assert score_receipt(gt, good)["exact"] is True
    assert score_receipt(gt, bad)["exact"] is False


def test_review_with_no_value_is_no_answer_not_wrong():  # decision 2a
    gt = {"total": {"total_price": "100"}}
    r1 = score_receipt(gt, {"menu": [], "total": amount("100")})
    r2 = score_receipt(gt, {"menu": [], "total": amount(None, "review")})
    total = summarize([r1, r2])["fields"]["total"]
    assert (total["correct"], total["wrong"], total["no_answer"]) == (1, 0, 1)
    assert total["precision"] == 1.0
    assert total["recall"] == 0.5


def test_review_but_answered_is_counted():
    gt = {"total": {"total_price": "100"}}
    r = score_receipt(gt, {"menu": [], "total": amount("100", "review")})
    assert summarize([r])["fields"]["total"]["review_but_answered"] == 1  