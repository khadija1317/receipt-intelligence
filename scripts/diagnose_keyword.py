"""Where does the right total value sit, and what word is beside it?
Validation only. Uses the frozen v1 cache to pick the failures.
Run: python -m scripts.diagnose_keyword
"""
import json
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.diagnose_total import DIR, cause
from src.extract_rules import _norm, classify, line_parts
from src.merge import merge_receipt
from src.score import label_fields, score_field

OCR = Path("cache/ocr")


def same_value(result, label):
    if result["status"] == "not_amount" or result["value"] is None:
        return False
    return Decimal(str(result["value"])) == label


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    tally = {"on a line": 0, "not on any line": 0, "word has 'tot' in it": 0}
    for i, raw in enumerate(ds["ground_truth"]):
        values, _ = label_fields(json.loads(raw)["gt_parse"], "IDR")
        if "total" not in values:
            continue
        ex = json.loads((DIR / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        outcome = score_field(values["total"], ex.get("total"))
        if outcome not in ("wrong", "no_answer"):
            continue
        bucket = cause(outcome, ex)
        if bucket.startswith("N1"):
            continue

        record = json.loads((OCR / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        lines = merge_receipt(record["pieces"])
        parsed = []
        for line in lines:
            label, amounts = line_parts(line, "IDR")
            parsed.append((label, amounts, line["text"]))

        hits = [n for n, (_, amounts, _) in enumerate(parsed)
                if any(same_value(a, values["total"]) for a in amounts)]
        print(f"\nval {i:3d} [{bucket[:2]}] label {values['total']}")
        if not hits:
            tally["not on any line"] += 1
            print("   value not on any merged line")
            continue
        tally["on a line"] += 1
        n = hits[-1]  # the lowest line holding the value
        if n > 0:
            print(f"   row {n-1} above: {parsed[n-1][2][:50]}")
        print(f"   row {n} HIT   : {parsed[n][2][:50]}   words='{parsed[n][0][:30]}'"
              f"   kind={classify(parsed[n][0])}")
        if n + 1 < len(parsed):
            print(f"   row {n+1} below: {parsed[n+1][2][:50]}")
        if "tot" in _norm(parsed[n][0]):
            tally["word has 'tot' in it"] += 1

    print("\nSUMMARY (38 non-N1 failures)")
    for k, v in tally.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()