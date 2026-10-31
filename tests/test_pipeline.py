import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts.run_validate import TOLERANCE as VALIDATE_TOLERANCE
from src import pipeline
from src.merge import merge_receipt


def piece(text, x, y, w, h=20, conf=0.95):
    return {"box": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
            "text": text, "conf": conf}


def made_up_receipt(rows):
    """rows = [(label, amount), ...] -> OCR pieces: a label on the left, an amount on the right."""
    pieces = []
    for n, (label, amount) in enumerate(rows):
        pieces.append(piece(label, 0, 40 * n, 200))
        pieces.append(piece(amount, 300, 40 * n, 100))
    return pieces


# ---- OCR as a subprocess (the subprocess itself is faked) ----

@pytest.fixture
def fake_python(tmp_path, monkeypatch):
    exe = tmp_path / "python.exe"
    exe.write_text("")
    monkeypatch.setattr(pipeline, "PADDLE_PYTHON", exe)
    return exe


def test_ocr_success_returns_the_record(fake_python, monkeypatch):
    def fake_run(command, **kwargs):
        out = command[command.index("--out") + 1]
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"pieces": [], "seconds": 1.0}, f)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    result = pipeline.run_ocr("receipt.png")
    assert result["ok"] is True
    assert result["record"]["seconds"] == 1.0


def test_ocr_timeout_gives_a_plain_message(fake_python, monkeypatch):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    result = pipeline.run_ocr("receipt.png", timeout=1)
    assert result["ok"] is False
    assert "longer than 1 seconds" in result["message"]


def test_ocr_exit_code_3_means_every_size_failed(fake_python, monkeypatch):
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda command, **kwargs: SimpleNamespace(returncode=3))
    result = pipeline.run_ocr("receipt.png")
    assert result["ok"] is False
    assert "at any size" in result["message"]


def test_ocr_crash_gives_a_plain_message(fake_python, monkeypatch):
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda command, **kwargs: SimpleNamespace(returncode=1))
    result = pipeline.run_ocr("receipt.png")
    assert result["ok"] is False
    assert "crashed" in result["message"]


def test_ocr_exit_zero_without_a_file_counts_as_a_crash(fake_python, monkeypatch):
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda command, **kwargs: SimpleNamespace(returncode=0))
    result = pipeline.run_ocr("receipt.png")
    assert result["ok"] is False
    assert "crashed" in result["message"]


def test_ocr_missing_venv_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "PADDLE_PYTHON", tmp_path / "nope.exe")
    result = pipeline.run_ocr("receipt.png")
    assert result["ok"] is False
    assert "was not found" in result["message"]


# ---- the stages and the verdict, on invented receipts ----

def test_consistent_receipt_passes_and_says_which_checks_could_not_run():
    # made up: two items add up to the total; no subtotal, no cash line
    pieces = made_up_receipt([("NASI GORENG", "17,500"), ("ES TEH", "5,000"), ("TOTAL", "22,500")])
    r = pipeline.run_stages(pieces)
    v = r["verdict"]
    assert v["state"] == "passed"
    assert (v["checks_ran"], v["checks_total"]) == (1, 3)
    assert [c["ran"] for c in r["checks"]] == [False, True, False]
    assert r["checks"][1]["gap"] == "0"
    assert r["checks"][0]["why_not"] == "no readable subtotal"
    assert r["checks"][2]["why_not"] == "neither a cash line nor a change line was found"


def test_total_that_disagrees_with_the_items_goes_to_review():
    # made up: items add up to 22,500 but the total line says 20,000
    pieces = made_up_receipt([("NASI GORENG", "17,500"), ("ES TEH", "5,000"), ("TOTAL", "20,000")])
    v = pipeline.run_stages(pieces)["verdict"]
    assert v["state"] == "review"
    assert [f["code"] for f in v["reasons"]] == ["TOTAL_VS_BASE"]
    assert "2,500" in v["reasons"][0]["reason"]


def test_receipt_without_a_total_line_is_queued_and_nothing_is_cross_checked():
    # made up: two items and no summary lines at all
    pieces = made_up_receipt([("NASI GORENG", "17,500"), ("ES TEH", "5,000")])
    r = pipeline.run_stages(pieces)
    v = r["verdict"]
    assert v["state"] == "review"
    assert [f["code"] for f in v["reasons"]] == ["MISSING_TOTAL"]
    assert v["checks_ran"] == 0
    assert r["checks"][1]["why_not"] == "no readable total"


def test_merge_view_shows_joined_pieces_in_braces():
    # made up: one amount split by the OCR into "17_" and "500"
    pieces = [piece("NASI GORENG", 0, 0, 200), piece("17_", 300, 0, 50), piece("500", 360, 0, 50)]
    rows = pipeline.merge_view(pieces, merge_receipt(pieces))
    assert rows[0]["merged"] == "NASI GORENG {17_500}"
    assert rows[0]["joined"] is True
    assert "17_ [0.95]" in rows[0]["raw"]


def test_every_stage_reports_its_seconds():
    pieces = made_up_receipt([("NASI GORENG", "17,500"), ("TOTAL", "17,500")])
    seconds = pipeline.run_stages(pieces)["seconds"]
    assert set(seconds) == {"merge", "repair", "extract", "render_text", "validate"}
    assert all(s >= 0 for s in seconds.values())


def test_tolerance_matches_the_frozen_validator_run():
    assert pipeline.TOLERANCE == VALIDATE_TOLERANCE


def test_load_example_missing_files_returns_none(tmp_path):
    assert pipeline.load_example("nope", folder=tmp_path) is None


def test_load_example_returns_cached_ocr(tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"not a real image")
    (tmp_path / "x_ocr.json").write_text(
        json.dumps({"pieces": [], "seconds": 2.0}), encoding="utf-8")
    example = pipeline.load_example("x", folder=tmp_path)
    assert example["ocr"]["ok"] is True
    assert example["ocr"]["source"] == "cache"
    assert example["ocr"]["wall_seconds"] is None
    assert example["image_path"].endswith("x.jpg")


@pytest.mark.parametrize("stem, state, code", [
    ("validation_000", "passed", None),
    ("validation_016", "review", "TOTAL_VS_BASE"),
    ("validation_066", "review", "MISSING_TOTAL"),
    ("validation_007", "review", "TOTAL_VS_BASE"),
])
def test_shipped_examples_give_the_verdicts_seen_on_validation(stem, state, code):
    example = pipeline.load_example(stem)
    assert example is not None
    verdict = pipeline.run_stages(example["ocr"]["record"]["pieces"])["verdict"]
    assert verdict["state"] == state
    if code:
        assert code in [f["code"] for f in verdict["reasons"]]
