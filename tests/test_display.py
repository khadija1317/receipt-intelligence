from src import display


def field(value, line="", status="ok", **extra):
    return {"value": value, "raw": value, "status": status, "conf": 0.9,
            "low_trust": False, "line": line, **extra}


CHECKS = [
    {"name": "Items vs subtotal", "ran": False, "gap": None, "why_not": "no readable subtotal"},
    {"name": "Total vs subtotal (or item sum)", "ran": True, "gap": "80,000", "why_not": None},
    {"name": "Cash minus change vs total", "ran": False, "gap": None, "why_not": "no change line found"},
]


def verdict(state, reasons=(), notes=()):
    return {"state": state, "reasons": list(reasons), "notes": list(notes),
            "checks_ran": 1, "checks_total": 3}


ARITH = {"code": "TOTAL_VS_BASE", "reason": "the closest match is still 80,000 off"}
MISSING = {"code": "MISSING_TOTAL", "reason": "no readable total on this receipt"}


def test_review_banner_names_the_reason_and_the_check_count():
    html = display.verdict_html(verdict("review", [ARITH]), CHECKS)
    assert "SEND TO REVIEW" in html
    assert "80,000 off" in html
    assert "<b>1 of 3</b>" in html
    assert "could not run (no change line found)" in html
    assert "29 of 30" in html


def test_arithmetic_reason_adds_the_cannot_say_which_is_wrong_line():
    html = display.verdict_html(verdict("review", [ARITH]), CHECKS)
    assert "not which one is wrong" in html


def test_missing_total_reason_does_not_add_that_line():
    html = display.verdict_html(verdict("review", [MISSING]), CHECKS)
    assert "not which one is wrong" not in html


def test_passed_banner_describes_the_checks_and_never_says_ok():
    html = display.verdict_html(verdict("passed"), CHECKS)
    assert "PASSED THE CHECKS" in html
    assert "LOOKS OK" not in html
    assert "282" in html
    assert "Items are not checked" in html
    assert "not that the receipt is right" in html


def test_banner_escapes_text():
    bad = {"code": "X", "reason": "<script>alert(1)</script>"}
    html = display.verdict_html(verdict("review", [bad]), CHECKS)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_notes_are_listed_when_present():
    note = {"code": "ZERO_PRICE", "reason": "1 item(s) have price 0"}
    html = display.verdict_html(verdict("passed", notes=[note]), CHECKS)
    assert "1 item(s) have price 0" in html
    assert "do not send a receipt to review" in html


def test_fields_rows_format_and_missing():
    record = {"total": field("100000", line="TOTAL 100,000"), "subtotal": None,
              "tax": field(None, status="review"), "service": None, "menu": []}
    rows = {r[0]: r for r in display.fields_rows(record)}
    assert rows["Total"][1] == "100,000"
    assert rows["Total"][4] == "TOTAL 100,000"
    assert rows["Subtotal"][1] == "not found"
    assert rows["Tax"][1] == "unreadable"


def test_adjacent_total_is_explained():
    record = {"total": field("22500", line="22,500 | TOTAL", adjacent="above"), "menu": []}
    row = display.fields_rows(record)[0]
    assert "line above" in row[4]


def test_items_rows_show_unreadable_prices():
    record = {"menu": [
        {"nm": "NASI GORENG", "cnt": "2", "price": field("35000")},
        {"nm": "ES TEH", "cnt": None, "price": field(None, status="review")},
    ]}
    assert display.items_rows(record) == [
        ["NASI GORENG", "2", "35,000", "ok"],
        ["ES TEH", "", "unreadable", "review"],
    ]


def test_check_rows():
    rows = display.check_rows(CHECKS)
    assert rows[1] == ["Total vs subtotal (or item sum)", "yes", "80,000", ""]
    assert rows[0] == ["Items vs subtotal", "no", "", "no readable subtotal"]


STAGES = {"merge": 0.0004, "repair": 0.0011, "extract": 0.0019, "render_text": 0.0007, "validate": 0.0008}


def test_timing_rows_for_a_live_upload():
    rows = display.timing_rows(STAGES, ocr_seconds=5.7, ocr_load_seconds=10.1,
                               ocr_wall_seconds=17.0, ocr_source="live")
    names = [r[0] for r in rows]
    assert "OCR: model loading" in names
    assert "OCR: whole subprocess" in names
    extractor = [r for r in rows if r[0].startswith("Extractor")][0]
    assert "includes its own merge and repair" in extractor[2]


def test_timing_rows_for_a_cached_example_do_not_claim_a_live_ocr():
    rows = display.timing_rows(STAGES, ocr_seconds=6.4, ocr_source="cache")
    names = [r[0] for r in rows]
    assert "OCR: model loading" not in names
    assert "cached" in rows[0][2]


def test_measured_numbers_add_up():
    m = display.MEASURED
    assert m["receipts"] - m["queued"] == m["not_queued"]
    assert m["wrong_value_queued"] + m["wrong_value_not_queued"] == m["wrong_value"]


def test_failure_banner_is_not_a_verdict():
    html = display.failure_html("OCR failed: the engine crashed")
    assert "NO RESULT" in html
    assert "not a verdict" in html
    assert "SEND TO REVIEW" not in html
    assert "PASSED" not in html


def test_failure_banner_escapes_the_message():
    html = display.failure_html("<b>x</b>")
    assert "<b>x</b>" not in html
    assert "&lt;b&gt;" in html
