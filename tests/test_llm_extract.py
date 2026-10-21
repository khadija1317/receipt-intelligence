import json
from pathlib import Path

import pytest

from src.llm_extract import (SCHEMA, answer_to_result, parse_reply,
                             render_receipt)


def _strict_ok(node):
    """Every object must list all its keys as required and forbid extra keys."""
    if isinstance(node, dict):
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert sorted(node["required"]) == sorted(node["properties"])
        for value in node.values():
            _strict_ok(value)
    elif isinstance(node, list):
        for value in node:
            _strict_ok(value)


def test_schema_follows_strict_mode_rules():
    _strict_ok(SCHEMA)


def test_amount_text_goes_through_parse_amount():
    answer = {"menu": [], "subtotal": {"amount": None, "evidence": None},
              "total": {"amount": "Rp. 45,500", "evidence": "TOTAL Rp. 45,500"},
              "tax": {"amount": None, "evidence": None},
              "service": {"amount": None, "evidence": None}}
    result = answer_to_result(answer, "IDR", 3)
    assert result["total"]["value"] == "45500"
    assert result["total"]["status"] == "ok"
    assert result["total"]["line"] == "TOTAL Rp. 45,500"
    assert result["subtotal"] is None   # null = no answer


def test_garbage_amount_becomes_review_not_a_value():
    answer = {"menu": [{"nm": "TEA", "cnt": None, "price": "n/a"}],
              "subtotal": {"amount": None, "evidence": None},
              "total": {"amount": "n/a", "evidence": "TOTAL n/a"},
              "tax": {"amount": None, "evidence": None},
              "service": {"amount": None, "evidence": None}}
    result = answer_to_result(answer, "IDR", 0)
    assert result["total"]["value"] is None
    assert result["total"]["status"] == "review"
    assert result["menu"][0]["price"]["value"] is None


def test_empty_string_counts_as_null():
    answer = {"menu": [], "subtotal": {"amount": "  ", "evidence": None},
              "total": {"amount": None, "evidence": None},
              "tax": {"amount": None, "evidence": None},
              "service": {"amount": None, "evidence": None}}
    assert answer_to_result(answer, "IDR", 0)["subtotal"] is None


def test_bad_json_gives_an_empty_flagged_record():
    assert parse_reply("this is not json") is None
    assert parse_reply("[1, 2]") is None
    result = answer_to_result(None, "IDR", 5)
    assert result["notes"]["llm_parse_error"] is True
    assert result["total"] is None and result["menu"] == []


from src.llm_extract import PROMPT_V1, PROMPT_V2


def test_v2_prompt_changes_only_rule_two():
    old, new = PROMPT_V1.splitlines(), PROMPT_V2.splitlines()
    assert len(old) == len(new)
    changed = [a for a, b in zip(old, new) if a != b]
    assert len(changed) == 1 and changed[0].startswith("2. total")
    assert "GRAND TOTAL" in PROMPT_V2 and "GRAND TOTAL" not in PROMPT_V1


OCR_FILE = Path("cache/ocr/validation_007.json")


@pytest.mark.skipif(not OCR_FILE.exists(), reason="OCR cache not present")
def test_render_keeps_val7_damage_as_printed():
    # REAL receipt (validation 7): the OCR read the total as 59,5005.
    pieces = json.loads(OCR_FILE.read_text(encoding="utf-8"))["pieces"]
    text = render_receipt(pieces, "IDR")
    assert "59,5005" in text     # damaged number reaches the LLM unchanged
    assert "63,636" in text