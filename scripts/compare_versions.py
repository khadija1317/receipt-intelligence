"""Which validation receipts changed outcome between two extractor versions?
Run: python -m scripts.compare_versions
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from datasets import load_dataset

from src.score import FIELDS, label_fields, score_field, to_decimal


def load(folder, i):
    path = Path(folder) / f"validation_{i:03d}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="cache/extract_rules_v1")
    ap.add_argument("--new", default="cache/extract_rules")
    args = ap.parse_args()

    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    for name in FIELDS:
        moves = Counter()
        rows = []
        for i, raw in enumerate(ds["ground_truth"]):
            values, _ = label_fields(json.loads(raw)["gt_parse"], "IDR")
            if name not in values:
                continue
            a, b = load(args.old, i), load(args.new, i)
            before = score_field(values[name], a.get(name))
            after = score_field(values[name], b.get(name))
            if before != after:
                moves[f"{before} -> {after}"] += 1
                rows.append((i, values[name], to_decimal(a.get(name)),
                             to_decimal(b.get(name)), before, after))
        print(f"\n{name.upper()}: {sum(moves.values())} receipts changed")
        for move, n in moves.items():
            print(f"  {move}: {n}")
        for i, label, old, new, before, after in rows:
            print(f"  val {i:3d}  label {label}  v1 {old}  v2 {new}  ({before} -> {after})")


if __name__ == "__main__":
    main()