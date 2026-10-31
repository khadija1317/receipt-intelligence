"""Print one case card for the Day 8 error-analysis sample (holdout B, rules v3 on Paddle text).

Run (.venv): python -m scripts.case_card --k 1 [--show]
k = 1..20, in the order: wrong-value missed, wrong-value caught, no total, false alarm.
Only indices saved in cache/scores/holdout_b_sample.json can be shown.
Read-only: changes nothing. --show opens the receipt image in your default viewer.
"""
import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.run_validate import CURRENCY, TOLERANCE
from src.llm_extract import render_receipt
from src.score import FIELDS, label_fields, label_items, score_receipt
from src.validate import find_cash_change, validate

SAMPLE = Path("cache/scores/holdout_b_sample.json")
OCR_DIR = "cache/ocr_paddle"
REC_DIR = "cache/extract_rules_v3_both"


def card_order(sample):
    w = sample["wrong_value"]
    cards = [(i, "wrong-value, MISSED by the validator") for i in w["missed"]]
    cards += [(i, "wrong-value, caught by the validator") for i in w["caught_sampled"]]
    cards += [(i, "no total (the extractor gave no total)") for i in sample["no_total"]]
    cards += [(i, "false alarm (clean by the scorer, but queued)") for i in sample["false_alarm"]]
    return cards


def field_text(rec, name):
    f = rec.get(name)
    if not f or f.get("value") is None:
        return "None"
    return f"{f['value']}  (status {f.get('status')}, line: {f.get('line')!r})"


def record_items(rec):
    items, unreadable = [], 0
    for m in rec.get("menu") or []:
        p = m.get("price") or {}
        try:
            items.append((m.get("nm"), Decimal(str(p["value"]))))
        except Exception:
            items.append((m.get("nm"), None))
            unreadable += 1
    return items, unreadable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    cards = card_order(sample)
    if not 1 <= args.k <= len(cards):
        ap.error(f"--k must be between 1 and {len(cards)}")
    i, pool = cards[args.k - 1]

    ds = load_dataset("naver-clova-ix/cord-v2", split="train")
    row = ds[i]
    gt = json.loads(row["ground_truth"])["gt_parse"]
    pieces = json.loads(Path(OCR_DIR, f"train_{i:03d}.json").read_text(encoding="utf-8"))["pieces"]
    text = render_receipt(pieces, CURRENCY)
    rec = json.loads(Path(REC_DIR, f"train_{i:03d}.json").read_text(encoding="utf-8"))
    res = score_receipt(gt, rec, CURRENCY)
    out = validate(rec, tolerance=TOLERANCE, text=text, currency=CURRENCY, grounding=False)

    print("=" * 72)
    print(f"CARD {args.k} of {len(cards)}   holdout B (CORD train) receipt {i}   pool: {pool}")
    print("=" * 72)
    print("\nMERGED + REPAIRED TEXT (what the extractor saw):")
    print(text)

    print("\nLABEL (CORD):")
    print("  total block    :", gt.get("total"))
    print("  sub_total block:", gt.get("sub_total"))
    lab_vals, unparseable = label_fields(gt, CURRENCY)
    print("  parsed fields  :", {k: str(v) for k, v in lab_vals.items()},
          "| unparseable:", unparseable)

    print("\nRECORD (rules v3 'both' on Paddle text):")
    for name in FIELDS:
        print(f"  {name:9}: {field_text(rec, name)}   -> scorer: {res['fields'][name]['outcome']}")

    lab_items, skipped = label_items(gt, CURRENCY)
    rec_items, unreadable = record_items(rec)
    print(f"\nITEMS: label {len(lab_items)} (skipped {skipped}), record {len(rec_items)} "
          f"(unreadable price {unreadable})")
    print("  label items :", [(it["nm"], str(it["price"])) for it in lab_items])
    print("  record items:", [(nm, None if p is None else str(p)) for nm, p in rec_items])
    lab_c = Counter(it["price"] for it in lab_items)
    rec_c = Counter(p for _nm, p in rec_items if p is not None)
    print("  prices only in the label :", sorted(str(p) for p in (lab_c - rec_c).elements()))
    print("  prices only in the record:", sorted(str(p) for p in (rec_c - lab_c).elements()))
    print("  scorer exact match:", res["exact"])

    print("\nVALIDATOR:")
    print("  in the review queue:", out["review"], "| any flag:", out["flagged"])
    for f in out["flags"]:
        print(f"    {f['code']:20} {f['reason']}")
    print("  gaps     :", {k: (None if v is None else str(v)) for k, v in out["gaps"].items()})
    print("  evaluated:", out["evaluated"])
    cc = find_cash_change(text, CURRENCY)
    print("  cash/change finder:", {k: (None if v is None else str(v)) for k, v in cc.items()})


    if args.show:
        row["image"].show()


if __name__ == "__main__":
    main()

