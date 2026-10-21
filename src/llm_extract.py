"""Arm 2: OCR text -> LLM -> a record in the same shape as the rules extractor.

This file has NO network code. It builds the prompt, defines the answer
format, and turns the LLM's answer (strings) into scorer-shaped values.
"""
import json

from src.merge import merge_receipt
from src.normalize import parse_amount
from src.repair import repair_token

MODEL = "openai/gpt-oss-120b"
FIELDS = ("subtotal", "total", "tax", "service")

PROMPT_V1 = """You will read the OCR text of one shop receipt. Each line of the text is one row of the receipt, from top to bottom. The OCR makes mistakes, so some words and numbers are damaged.

Return one JSON object that follows the schema. Rules:

1. Copy every amount exactly as it appears in the text, with its dots, commas and spaces. Never calculate, correct, round or guess a digit. If a number on a line looks damaged, copy it as it is.
2. total: the amount on the line labelled TOTAL. The OCR may misspell the word (for example "Tota]"). Do not use a SUBTOTAL line, a CASH, PAYMENT or CHANGE line, or a line such as "Total Qty" or "Total Item". If no line is labelled TOTAL, or that line has no amount, return null.
3. subtotal: the amount on the line labelled SUBTOTAL or SUB TOTAL. Return null if there is none.
4. tax: the amount on a tax line (labels such as TAX, PB1, PPN, PAJAK). Return null if there is none.
5. service: the amount on a service charge line. Return null if there is none.
6. For each of these four fields, evidence is the full text of the line the amount was copied from, copied exactly. When the amount is null, the evidence is null.
7. menu: one entry for each purchased item that has a name and an amount on its line, in the order they appear. Do not list total, tax, service, payment or change lines. nm is the item name as written. cnt is the quantity if the line shows one, otherwise null. price is the amount printed on that line (the line total), copied as in rule 1; it is null if the line has no amount."""
_RULE2_V1 = (
    '2. total: the amount on the line labelled TOTAL. The OCR may misspell the word '
    '(for example "Tota]"). Do not use a SUBTOTAL line, a CASH, PAYMENT or CHANGE line, '
    'or a line such as "Total Qty" or "Total Item". If no line is labelled TOTAL, or that '
    'line has no amount, return null.')
_RULE2_V2 = (
    '2. total: the amount on the line labelled TOTAL. A line labelled GRAND TOTAL or '
    'GRANDTOTAL is a TOTAL line. The OCR may misspell the word (for example "Tota]"). '
    'If more than one line is labelled TOTAL (for example TOTAL, then GRAND TOTAL below it), '
    'use the lowest one on the receipt. If that line shows more than one amount, use the '
    'rightmost amount. Do not use a SUBTOTAL line, a CASH, PAYMENT or CHANGE line, '
    'or a line such as "Total Qty" or "Total Item". If no line is labelled TOTAL, or that '
    'line has no amount, return null.')
assert _RULE2_V1 in PROMPT_V1          # fails loudly if rule 2 was retyped differently
PROMPT_V2 = PROMPT_V1.replace(_RULE2_V1, _RULE2_V2)
PROMPTS = {"v1": PROMPT_V1, "v2": PROMPT_V2}
SYSTEM_PROMPT = PROMPT_V1              # default, so existing imports keep working
_TEXT_OR_NULL = {"anyOf": [{"type": "string"}, {"type": "null"}]}


def _summary_schema():
    return {
        "type": "object",
        "properties": {"amount": _TEXT_OR_NULL, "evidence": _TEXT_OR_NULL},
        "required": ["amount", "evidence"],
        "additionalProperties": False,
    }


# Strict mode needs: every key listed in "required", no extra keys allowed.
SCHEMA = {
    "type": "object",
    "properties": {
        "menu": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"nm": {"type": "string"},
                               "cnt": _TEXT_OR_NULL,
                               "price": _TEXT_OR_NULL},
                "required": ["nm", "cnt", "price"],
                "additionalProperties": False,
            },
        },
        "subtotal": _summary_schema(),
        "total": _summary_schema(),
        "tax": _summary_schema(),
        "service": _summary_schema(),
    },
    "required": ["menu", "subtotal", "total", "tax", "service"],
    "additionalProperties": False,
}


def _show(result):
    """How one amount token appears in the text the LLM reads."""
    if result["status"] == "repaired" and result["value"] is not None:
        return str(result["value"])      # the repaired number, digits only
    return result["raw"].strip()         # printed as the OCR gave it


def render_line(line, currency="IDR"):
    """One merged line -> text. Tokens keep their order, two spaces between them."""
    out = []
    for token in line["tokens"]:
        result = repair_token(token, currency)
        if result["status"] != "not_amount":
            out.append(_show(result))
            continue
        parts = token["text"].split()
        if len(parts) > 1:  # 'TOTAL 60.000' in one piece: same last-word trial as the rules arm
            last = repair_token({**token, "text": parts[-1], "no_separator": False}, currency)
            if last["status"] != "not_amount":
                out.append(" ".join(parts[:-1]))
                out.append(_show(last))
                continue
        out.append(token["text"])
    return "  ".join(out)


def render_receipt(pieces, currency="IDR"):
    """Raw OCR pieces -> merged + repaired lines -> one text block."""
    lines = [render_line(line, currency) for line in merge_receipt(pieces)]
    return "\n".join(text for text in lines if text.strip())


def build_messages(text, prompt=None):
    # Fixed instructions first, receipt text last: the fixed part can be cached.
    return [{"role": "system", "content": prompt or SYSTEM_PROMPT},
            {"role": "user", "content": text}]

def parse_reply(content):
    """The LLM's reply text -> a dict, or None if it is not a JSON object."""
    try:
        answer = json.loads(content)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def _amount(text, currency):
    """An amount STRING from the LLM -> the same dict shape the scorer reads."""
    if text is None or not str(text).strip():
        return {"value": None, "raw": None, "status": "review", "conf": None}
    raw = str(text).strip()
    try:
        value = parse_amount(raw, currency)   # the same normalizer the rules arm is judged by
    except ValueError:                        # AmountParseError is a ValueError
        return {"value": None, "raw": raw, "status": "review", "conf": None}
    return {"value": str(value), "raw": raw, "status": "ok", "conf": None}


def answer_to_result(answer, currency, index):
    """The LLM's answer -> a record shaped like cache/extract_rules files."""
    result = {"menu": [], "notes": {"llm_parse_error": answer is None}, "index": index}
    for kind in FIELDS:
        result[kind] = None
    if answer is None:
        return result
    for item in answer.get("menu") or []:
        if isinstance(item, dict):
            name = " ".join(str(item.get("nm") or "").split())   # collapse the double spaces
            result["menu"].append({"nm": name, "cnt": item.get("cnt"),
                                   "price": _amount(item.get("price"), currency)})
    for kind in FIELDS:
        block = answer.get(kind)
        if not isinstance(block, dict):
            continue
        amount = block.get("amount")
        if amount is None or not str(amount).strip():
            continue                          # null from the LLM = "no answer" (decision 2a)
        field = _amount(amount, currency)
        field["line"] = block.get("evidence")
        result[kind] = field
    return result