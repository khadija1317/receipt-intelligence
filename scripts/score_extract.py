"""Score cached extractor output against the labels.
Run: python -m scripts.score_extract                      (validation, v1)
     python -m scripts.score_extract --split test         (counts only)
"""
import argparse
import json
import sys
from pathlib import Path

from datasets import load_dataset

from src.dataset import check_test_set
from src.score import FIELDS, score_receipt, summarize

CURRENCY = "IDR"  # CORD is configured as rupiah


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["test", "validation"], default="validation")
    ap.add_argument("--dir", default="cache/extract_rules")
    ap.add_argument("--tag", default="v1")
    args = ap.parse_args()

    ds = load_dataset("naver-clova-ix/cord-v2", split=args.split)
    if args.split == "test":
        check_test_set(ds)  # must run before any test scoring
    labels = ds["ground_truth"]  # only the label column, no images

    results = []
    for i, raw in enumerate(labels):
        path = Path(args.dir) / f"{args.split}_{i:03d}.json"
        if not path.exists():
            sys.exit(f"Missing {path}. Run the extractor on this split first.")
        extracted = json.loads(path.read_text(encoding="utf-8"))
        gt_parse = json.loads(raw)["gt_parse"]
        results.append(score_receipt(gt_parse, extracted, CURRENCY))

    s = summarize(results)
    print(f"\nsplit={args.split}  extractor={args.tag}  receipts={s['receipts']}")

    print("\nFIELDS (only receipts whose label has the field are scored)")
    print(f"{'field':9} {'correct':>7} {'wrong':>5} {'no_ans':>6} {'extra':>5} "
          f"{'unscored':>8} {'badlabel':>8} {'prec':>7} {'recall':>7} {'f1':>7}")
    for name in FIELDS:
        f = s["fields"][name]
        print(f"{name:9} {f['correct']:7d} {f['wrong']:5d} {f['no_answer']:6d} "
              f"{f['extra']:5d} {f['not_scored']:8d} {f['unparseable_label']:8d} "
              f"{pct(f['precision']):>7} {pct(f['recall']):>7} {pct(f['f1']):>7}")
    for name in FIELDS:
        n = s["fields"][name]["review_but_answered"]
        if n:
            print(f"note: {name}: {n} fields had status 'review' but still carried a value")

    it = s["items"]
    print("\nITEMS (top-level, matched by price only, decision 1a)")
    print(f"  matched {it['matched']}, returned {it['returned']}, "
          f"label items {it['label_count']}, unreadable price {it['unreadable']}")
    print(f"  precision {pct(it['precision'])}   recall {pct(it['recall'])}")
    print(f"  side numbers on matched pairs: name similarity {pct(it['name_similarity'])}, "
          f"count agreement {pct(it['count_agreement'])}")
    print(f"  label items skipped: {s['label_items_skipped']}")

    print(f"\nRECEIPT EXACT MATCH: {s['exact']} of {s['receipts']}")

    if args.split == "validation":  # indices are only printed on validation
        for outcome in ("wrong", "no_answer"):
            idx = [i for i, r in enumerate(results)
                   if r["fields"]["total"]["outcome"] == outcome]
            print(f"\ntotal '{outcome}' on validation ({len(idx)}): {idx}")

    out = Path("cache/scores")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.split}_{args.tag}.json").write_text(
        json.dumps(s, indent=1, default=str), encoding="utf-8")  # summary only
    print(f"\nsummary saved to cache/scores/{args.split}_{args.tag}.json")


if __name__ == "__main__":
    main()