import argparse
import json
import re
from pathlib import Path

from datasets import load_dataset

from scripts.total_visible import try_parse

CACHE = Path("cache/ocr")
SPLIT = "validation"  # deliberately hard-coded: this script never touches test


def digits(text):
    return re.sub(r"\D", "", text)


def one_digit_off(a, b):
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", type=int, default=8,
                        help="print piece details for the first N misses")
    args = parser.parse_args()

    ds = load_dataset("naver-clova-ix/cord-v2", split=SPLIT)
    labels = ds["ground_truth"]

    tally = {"fragment": 0, "misread": 0, "both": 0, "neither": 0}
    shown = 0

    for i, raw in enumerate(labels):
        total = json.loads(raw)["gt_parse"].get("total", {})
        label_text = total.get("total_price") if isinstance(total, dict) else None
        if label_text is None:
            continue
        target = try_parse(str(label_text))
        if target is None:
            continue

        record = json.loads((CACHE / f"{SPLIT}_{i:03d}.json").read_text(encoding="utf-8"))
        pieces = record["pieces"]
        texts = [p["text"] for p in pieces]
        if any(try_parse(t) == target for t in texts) or \
           any(try_parse(w) == target for t in texts for w in t.split()):
            continue  # this receipt is a hit, not a miss

        td = str(int(abs(target)))
        tags = {}
        for p in pieces:
            pd = digits(p["text"])
            tag = ""
            if len(pd) >= 2 and set(pd) != {"0"} and pd != td and pd in td:
                tag = "fragment"
            elif one_digit_off(pd, td):
                tag = "misread"
            tags[id(p)] = tag

        has_frag = "fragment" in tags.values()
        has_mis = "misread" in tags.values()
        key = "both" if (has_frag and has_mis) else "fragment" if has_frag \
            else "misread" if has_mis else "neither"
        tally[key] += 1

        if shown < args.show:
            shown += 1
            print(f"\n=== validation {i}: label total = {label_text!r} "
                  f"(value {target}) -> bucket: {key}")
            rows = []
            for p in pieces:
                if not re.search(r"\d", p["text"]):
                    continue
                ys = [pt[1] for pt in p["box"]]
                xs = [pt[0] for pt in p["box"]]
                rows.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), p))
            for yc, xl, h, p in sorted(rows, key=lambda r: (r[0], r[1])):
                mark = f"  <-- {tags[id(p)]}" if tags[id(p)] else ""
                print(f"  y={yc:6.0f} x={xl:4d} h={h:3d} conf={p['conf']:.2f}  "
                      f"{p['text']!r}{mark}")

    print("\nBucket tally over all validation misses:", tally)


if __name__ == "__main__":
    main()