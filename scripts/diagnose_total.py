"""Why did v1 miss the total on validation? Counts causes from the v1 cache only.
Run: python -m scripts.diagnose_total
"""
import json
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset

from src.score import label_fields, score_field, to_decimal

DIR = Path("cache/extract_rules_v1")  # the frozen v1 files


def cause(outcome, extracted):
    if outcome == "wrong":
        return "W  wrong number returned"
    if extracted.get("total") is not None:  # a field exists but has no value
        return "N1 total line found, amount unreadable"
    if "total" in extracted["notes"]["keyword_without_amount"]:
        return "N2 word 'total' found, no amount on that row"
    return "N3 no total line found at all"


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    groups = defaultdict(list)
    for i, raw in enumerate(ds["ground_truth"]):
        gt_parse = json.loads(raw)["gt_parse"]
        values, _ = label_fields(gt_parse, "IDR")
        if "total" not in values:
            continue  # no total label: not scored
        extracted = json.loads((DIR / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        outcome = score_field(values["total"], extracted.get("total"))
        if outcome in ("wrong", "no_answer"):
            groups[cause(outcome, extracted)].append((i, values["total"], extracted))

    print(f"failures: {sum(len(v) for v in groups.values())}")
    for name in sorted(groups):
        print(f"\n{name}: {len(groups[name])}")
        for i, label, ex in groups[name]:
            got = to_decimal(ex.get("total"))
            line = (ex["total"] or {}).get("line", "")[:45]
            n = ex["notes"]
            print(f"  val {i:3d}  label {label}  got {got}  line '{line}'  "
                  f"items {len(ex['menu'])}  orphans {n['orphan_amount_lines']}  "
                  f"kw-no-amount {n['keyword_without_amount']}")


if __name__ == "__main__":
    main()