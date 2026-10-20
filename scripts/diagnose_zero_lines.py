"""Zero prices: which lines do they come from, and where does the label itself have a 0?
Validation only.
Run: python -m scripts.diagnose_zero_lines
"""
import json
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from src.extract_rules import line_parts
from src.merge import merge_receipt
from src.score import label_items

OCR = Path("cache/ocr")
EXTRACTED_ZERO = (36, 38, 43, 47, 64, 66, 75, 78, 99)


def is_zero(result):
    return result["value"] is not None and Decimal(str(result["value"])) == 0


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")

    print("PART 1: label items whose price is 0")
    for i, raw in enumerate(ds["ground_truth"]):
        labels, _ = label_items(json.loads(raw)["gt_parse"], "IDR")
        zeros = [lab for lab in labels if lab["price"] == 0]
        if zeros:
            print(f"  val {i:3d}  {len(zeros)} of {len(labels)} label items: "
                  f"{[lab['nm'] for lab in zeros]}")

    print("\nPART 2: merged lines whose last amount is 0, in the 9 receipts")
    for i in EXTRACTED_ZERO:
        path = OCR / f"validation_{i:03d}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        for line in merge_receipt(record["pieces"]):
            label, amounts = line_parts(line, "IDR")
            if amounts and is_zero(amounts[-1]):
                shown = [(a["raw"], a["status"]) for a in amounts]
                print(f"  val {i:3d}  line: {line['text'][:60]}")
                print(f"           amounts left to right: {shown}")


if __name__ == "__main__":
    main()