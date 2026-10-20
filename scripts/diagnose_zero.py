"""Zero-valued amounts in the extractor output (validation only).
Run: python -m scripts.diagnose_zero
"""
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from src.score import FIELDS, label_items, to_decimal

DIR = Path("cache/extract_rules")  # v2 output on validation


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    zero_receipts, zero_items = set(), 0
    status_tally = Counter()
    label_zero_items = 0
    for i, raw in enumerate(ds["ground_truth"]):
        gt_parse = json.loads(raw)["gt_parse"]
        labels, _ = label_items(gt_parse, "IDR")
        label_zero_items += sum(1 for lab in labels if lab["price"] == 0)

        ex = json.loads((DIR / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        zeros = [m for m in ex["menu"] if to_decimal(m["price"]) == Decimal(0)]
        if zeros:
            zero_receipts.add(i)
            zero_items += len(zeros)
            print(f"val {i:3d}  {len(zeros)} zero item(s) of {len(ex['menu'])} items")
            for m in zeros:
                p = m["price"]
                status_tally[p["status"]] += 1
                print(f"     '{m['nm'][:28]}'  raw='{p['raw']}'  status={p['status']}  "
                      f"conf={p['conf']:.2f}  cnt={m['cnt']}")
        for name in FIELDS:
            if to_decimal(ex.get(name)) == Decimal(0):
                print(f"val {i:3d}  SUMMARY FIELD {name} = 0  raw='{ex[name]['raw']}'  "
                      f"status={ex[name]['status']}")

    print(f"\nreceipts with a zero-price item: {len(zero_receipts)}")
    print(f"zero-price items: {zero_items}  (by status: {dict(status_tally)})")
    print(f"label items with price 0 (all validation): {label_zero_items}")


if __name__ == "__main__":
    main()