import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from datasets import load_dataset

from scripts.sweep_join_gap import label_amounts
from scripts.total_visible import try_parse
from src.dataset import check_test_set
from src.merge import merge_receipt
from src.repair import repair_token

CURRENCY = "IDR"
CACHE = Path("cache/ocr")


def token_results(token):
    """Repair a token; if the whole token isn't an amount but holds several
    words ('TOTAL 60.000' in one piece), try each word, as Day 2 did."""
    whole = repair_token(token, CURRENCY)
    if whole["status"] != "not_amount" or " " not in token["text"].strip():
        return [whole]
    return [repair_token({**token, "text": w, "no_separator": False}, CURRENCY)
            for w in token["text"].split()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "validation"], default="test")
    split = parser.parse_args().split

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    if split == "test":
        check_test_set(ds)

    scored = 0
    hit_clean, hit_repaired, missed = 0, 0, []
    repair_kinds = Counter()
    letter_total, letter_match = Counter(), Counter()

    for i, raw in enumerate(ds["ground_truth"]):
        gt = json.loads(raw)["gt_parse"]
        total = gt.get("total", {})
        label_text = total.get("total_price") if isinstance(total, dict) else None
        if label_text is None:
            continue
        target = try_parse(str(label_text))
        if target is None:
            continue
        scored += 1

        path = CACHE / f"{split}_{i:03d}.json"
        if not path.exists():
            sys.exit(f"Missing {path}")
        record = json.loads(path.read_text(encoding="utf-8"))
        results = [r for line in merge_receipt(record["pieces"])
                   for t in line["tokens"] for r in token_results(t)]

        for r in results:
            if r["status"] == "repaired":
                for kind in r["repairs"]:
                    repair_kinds[kind] += 1

        matching = [r for r in results if r["value"] is not None and r["value"] == target]
        if any(r["status"] == "ok" for r in matching):
            hit_clean += 1
        elif matching:
            hit_repaired += 1
        else:
            missed.append(i)

        if split == "validation":
            amounts = label_amounts(gt, set())
            for r in results:
                if r["status"] == "repaired":
                    for ch in set(r["letters"]):
                        letter_total[ch] += 1
                        if r["value"] is not None and abs(r["value"]) in amounts:
                            letter_match[ch] += 1

    hits = hit_clean + hit_repaired
    print(f"split: {split}   scored receipts: {scored}")
    print(f"MERGED total-visible rate: {hits} of {scored} = {100 * hits / scored:.1f}%")
    print(f"  hit with an unrepaired token:      {hit_clean}")
    print(f"  hit only through a repaired token: {hit_repaired}")
    print(f"repairs applied (all tokens, all receipts): {dict(repair_kinds)}")

    if split == "validation":
        print(f"misses (OK to inspect): {missed}")
        print("\nzero-like letters inside repaired tokens: letter -> used / value matches a label")
        for ch in sorted(letter_total):
            print(f"  {ch!r}: {letter_total[ch]} / {letter_match[ch]}")
    else:
        print("(test split: counts only, no receipt indices)")


if __name__ == "__main__":
    main()