import argparse
import json
from pathlib import Path

from src.geometry import group_rows
from src.merge import JOIN_GAP, gap_ratio, merge_receipt, shape_match

CACHE = Path("cache/ocr")
SPLIT = "validation"  # deliberately hard-coded: this script never touches test


def load_pieces(i):
    path = CACHE / f"{SPLIT}_{i:03d}.json"
    return json.loads(path.read_text(encoding="utf-8"))["pieces"]


def list_pairs():
    joined, rejected = [], []
    for i in range(100):
        for row in group_rows(load_pieces(i)):
            for left, right in zip(row, row[1:]):
                if not shape_match(left, right):
                    continue
                ratio = gap_ratio(left, right)
                item = (i, left["text"], right["text"], ratio)
                (joined if ratio <= JOIN_GAP else rejected).append(item)
    print(f"Pairs that match the shape and gap <= {JOIN_GAP}  (JOINED): {len(joined)}")
    for i, a, b, r in joined:
        print(f"  val {i:3d}: {a!r:12} + {b!r:10} gap={r:5.2f}h")
    print(f"\nPairs that match the shape but gap > {JOIN_GAP}  (REJECTED): {len(rejected)}")
    for i, a, b, r in rejected:
        print(f"  val {i:3d}: {a!r:12} + {b!r:10} gap={r:5.2f}h")


def show_lines(i):
    print(f"\n=== validation {i}  (joined tokens shown in {{braces}})")
    for line in merge_receipt(load_pieces(i)):
        text = " ".join("{" + t["text"] + "}" if t["joined"] else t["text"]
                        for t in line["tokens"])
        print(f"  y~{line['y_center']:5.0f}  conf>={line['min_conf']:.2f}  {text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=int, nargs="+", default=[0, 19, 7])
    args = parser.parse_args()
    list_pairs()
    for i in args.receipts:
        show_lines(i)


if __name__ == "__main__":
    main()