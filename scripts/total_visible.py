import argparse
import json
import statistics
import sys
from pathlib import Path

from datasets import load_dataset

from src.dataset import check_test_set
from src.normalize import parse_amount

CURRENCY = "IDR"
CACHE = Path("cache/ocr")


def try_parse(text):
    """Return a Decimal, or None if the normalizer refuses the text."""
    try:
        return parse_amount(text, CURRENCY)
    except ValueError:  # AmountParseError is a ValueError
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "validation"], default="test")
    parser.add_argument("--ocr-dir", default="cache/ocr")
    args = parser.parse_args()
    split = args.split
    cache = Path(args.ocr_dir)

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    if split == "test":
        check_test_set(ds)
    labels = ds["ground_truth"]

    no_total = []          # receipts with no total_price in the ground truth
    unparseable = []       # (index, label text) the normalizer refuses, e.g. "(0)"
    strict_hits = []       # a whole piece parses to the total
    loose_hits = []        # whole piece OR any word in a piece parses to the total
    all_seconds = []
    scored = 0

    for i, raw in enumerate(labels):
        path = cache / f"{split}_{i:03d}.json"
        if not path.exists():
            sys.exit(f"Missing {path}. Has the OCR run for '{split}' finished?")
        record = json.loads(path.read_text(encoding="utf-8"))
        all_seconds.append(record["seconds"])

        total = json.loads(raw)["gt_parse"].get("total", {})
        label_text = total.get("total_price") if isinstance(total, dict) else None
        if label_text is None:
            no_total.append(i)
            continue

        target = try_parse(str(label_text))
        if target is None:
            unparseable.append((i, label_text))
            continue

        scored += 1
        texts = [p["text"] for p in record["pieces"]]

        strict = any(try_parse(t) == target for t in texts)
        word = any(try_parse(w) == target for t in texts for w in t.split())

        if strict:
            strict_hits.append(i)
        if strict or word:
            loose_hits.append(i)

    print(f"split: {split}")
    if split == "validation":
        print(f"receipts with no total_price: {len(no_total)} -> {no_total}")
        print(f"unparseable total labels: {len(unparseable)} -> {unparseable}")
    else:
        print(f"receipts with no total_price: {len(no_total)}")
        print(f"unparseable total labels: {len(unparseable)}")
        
    print(f"scored receipts: {scored}")
    print(f"strict (whole piece):         {len(strict_hits)} of {scored}")
    print(f"HEADLINE (piece or any word): {len(loose_hits)} of {scored}"
          f"  = {100 * len(loose_hits) / scored:.1f}%")
    print(f"median seconds per image (all {len(all_seconds)}): "
          f"{statistics.median(all_seconds):.1f}")

    if split == "validation":
        missed = [i for i in range(len(labels))
                  if i not in loose_hits and i not in no_total
                  and i not in [u[0] for u in unparseable]]
        print(f"validation misses (OK to inspect): {missed}")


if __name__ == "__main__":
    main()