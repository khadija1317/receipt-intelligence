import argparse
import json
import re
from pathlib import Path

from src.geometry import group_rows

CACHE = Path("cache/ocr")
SPLIT = "validation"  # deliberately hard-coded: this script never touches test

BINS = [
    ("< 0.25 (incl. overlap)", float("-inf"), 0.25),
    ("0.25 - 0.5", 0.25, 0.5),
    ("0.5 - 1", 0.5, 1),
    ("1 - 2", 1, 2),
    ("2 - 4", 2, 4),
    ("> 4", 4, float("inf")),
]


def load_rows(i):
    path = CACHE / f"{SPLIT}_{i:03d}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    return group_rows(record["pieces"])


def gap_ratio(left, right):
    gap = right["x_left"] - left["x_right"]
    ref = max(min(left["h"], right["h"]), 1)
    return gap, gap / ref


def show_receipt(i):
    rows = load_rows(i)
    print(f"\n=== validation {i}: {len(rows)} rows (showing rows with 2+ pieces)")
    for row in rows:
        if len(row) < 2:
            continue
        y = sum(b["y_center"] for b in row) / len(row)
        parts = []
        for k, b in enumerate(row):
            parts.append(f"{b['text']!r}[{b['x_left']}-{b['x_right']}]")
            if k + 1 < len(row):
                gap, ratio = gap_ratio(b, row[k + 1])
                parts.append(f"--{gap}px={ratio:.2f}h-->")
        print(f"  y~{y:5.0f}: " + " ".join(parts))


def histogram():
    counts_all = [0] * len(BINS)
    counts_digits = [0] * len(BINS)
    for i in range(100):
        for row in load_rows(i):
            for left, right in zip(row, row[1:]):
                _, ratio = gap_ratio(left, right)
                both_digits = bool(re.search(r"\d", left["text"])
                                   and re.search(r"\d", right["text"]))
                for k, (_, lo, hi) in enumerate(BINS):
                    if lo <= ratio < hi:
                        counts_all[k] += 1
                        if both_digits:
                            counts_digits[k] += 1
                        break
    print("\nGap / text height, adjacent pieces on the same row, all 100 validation receipts")
    print(f"{'bin':26s}{'all pairs':>10s}{'both have a digit':>20s}")
    for (label, _, _), a, d in zip(BINS, counts_all, counts_digits):
        print(f"{label:26s}{a:10d}{d:20d}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=int, nargs="+", default=[0, 3, 19, 80, 7])
    args = parser.parse_args()
    for i in args.receipts:
        show_receipt(i)
    histogram()


if __name__ == "__main__":
    main()