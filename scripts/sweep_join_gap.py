import json
import re
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.total_visible import try_parse
from src.geometry import group_rows
from src.merge import ZEROISH, gap_ratio, shape_match, squash

CACHE = Path("cache/ocr")
SPLIT = "validation"  # deliberately hard-coded: this script never touches test
THRESHOLDS = [0.3, 0.6, 0.8, 1.0, 1.2]
LIST_ABOVE = 0.6      # always list pairs above the current threshold
ZERO_MAP = str.maketrans({c: "0" for c in ZEROISH})


def label_amounts(node, found):
    """Collect every string in the ground truth that parses as an amount."""
    if isinstance(node, dict):
        for v in node.values():
            label_amounts(v, found)
    elif isinstance(node, list):
        for v in node:
            label_amounts(v, found)
    elif isinstance(node, str):
        value = try_parse(node)
        if value is not None:
            found.add(abs(value))
    return found


def joined_value(left, right):
    text = (squash(left["text"]) + squash(right["text"])).translate(ZERO_MAP)
    return Decimal(re.sub(r"\D", "", text))


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split=SPLIT)
    pairs = []
    for i, raw in enumerate(ds["ground_truth"]):
        amounts = label_amounts(json.loads(raw)["gt_parse"], set())
        path = CACHE / f"{SPLIT}_{i:03d}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        for row in group_rows(record["pieces"]):
            for left, right in zip(row, row[1:]):
                if shape_match(left, right):
                    value = joined_value(left, right)
                    pairs.append({
                        "i": i, "left": left["text"], "right": right["text"],
                        "ratio": gap_ratio(left, right),
                        "value": value, "match": value in amounts,
                    })

    print(f"{'threshold':>10}{'joined':>8}{'match a label':>15}{'no match':>10}")
    for t in THRESHOLDS:
        chosen = [p for p in pairs if p["ratio"] <= t]
        hit = sum(p["match"] for p in chosen)
        print(f"{t:10.1f}{len(chosen):8d}{hit:15d}{len(chosen) - hit:10d}")

    print(f"\nPairs above {LIST_ABOVE}, or without a label match (look at these images):")
    for p in sorted(pairs, key=lambda p: p["ratio"]):
        if p["ratio"] > LIST_ABOVE or not p["match"]:
            tag = "MATCH   " if p["match"] else "no match"
            print(f"  {tag} val {p['i']:3d}: {p['left']!r:10} + {p['right']!r:8} "
                  f"gap={p['ratio']:5.2f}h  value={p['value']}")


if __name__ == "__main__":
    main()