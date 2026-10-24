import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.total_visible import try_parse
from src.dataset import check_test_set
from src.extract_rules import extract_receipt

CURRENCY = "IDR"
OCR = Path("cache/ocr")
OUT = Path("cache/extract_rules")


def show(result):
    print(f"\n=== receipt {result['index']}")
    for m in result["menu"]:
        p = m["price"]
        print(f"  item: {m['nm']!r}  cnt={m['cnt']}  price={p['value']} ({p['status']})")
    for key in ("subtotal", "service", "tax", "total"):
        f = result[key]
        text = "MISSING" if f is None else f"{f['value']} ({f['status']})  from line {f['line']!r}"
        print(f"  {key:9s}: {text}")
    print("  notes:", result["notes"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "validation"], default="validation")
    parser.add_argument("--show", type=int, nargs="*", default=[0, 19, 7])
    parser.add_argument("--ocr-dir", default="cache/ocr")
    parser.add_argument("--out-dir", default="cache/extract_rules")
    parser.add_argument("--adjacent", choices=["off", "above", "both"], default="off")
    args = parser.parse_args()
    split = args.split
    ocr = Path(args.ocr_dir)
    out = Path(args.out_dir)

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    if split == "test":
        check_test_set(ds)
    out.mkdir(parents=True, exist_ok=True)

    tally = Counter()
    quick_hit = quick_n = with_subs = 0

    for i, raw in enumerate(ds["ground_truth"]):
        record = json.loads((ocr / f"{split}_{i:03d}.json").read_text(encoding="utf-8"))
        result = extract_receipt(record["pieces"], CURRENCY, adjacent=args.adjacent)
        result["index"] = i
        (out / f"{split}_{i:03d}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

        tally["receipts"] += 1
        for key in ("subtotal", "service", "tax", "total"):
            tally[f"{key} found"] += result[key] is not None
        tally["total found but unreadable"] += bool(
            result["total"] and result["total"]["value"] is None)
        tally["receipts with no items"] += not result["menu"]
        tally["keyword line with no amount on it"] += bool(
            result["notes"]["keyword_without_amount"])
        tally["receipts with orphan amount lines"] += result["notes"]["orphan_amount_lines"] > 0

        if split == "validation":  # development split: labels may be looked at
            gt = json.loads(raw)["gt_parse"]
            menu = gt.get("menu", [])
            menu = [menu] if isinstance(menu, dict) else menu
            with_subs += any("sub" in m for m in menu)
            total = gt.get("total", {})
            label = total.get("total_price") if isinstance(total, dict) else None
            target = try_parse(str(label)) if label is not None else None
            if target is not None:
                quick_n += 1
                got = result["total"] and result["total"]["value"]
                quick_hit += got is not None and Decimal(got) == target
        if i in args.show and split == "validation":
            show(result)

    print(f"\nwrote {tally['receipts']} files to {out}")
    for key, value in tally.items():
        print(f"  {key}: {value}")
    if split == "validation":
        print(f"\nvalidation receipts with sub-items in the labels: {with_subs}")
        print(f"quick sanity check (NOT the Day 4 scorer): extracted total equals "
              f"label total on {quick_hit} of {quick_n}")


if __name__ == "__main__":
    main()