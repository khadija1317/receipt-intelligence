"""Run the frozen validator on the four pipelines and print the headline numbers.

Run: python -m scripts.run_validate --split validation
     python -m scripts.run_validate --split test        (counts only, no indices)
"""
import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.total_visible import try_parse
from src.dataset import check_test_set
from src.llm_extract import render_receipt
from src.score import score_receipt
from src.validate import QUEUE_CODES, VALUE_CODES, find_cash_change, validate

CURRENCY = "IDR"
TOLERANCE = Decimal(1)  # frozen on Day 7, chosen from the validation table
FIELDS = ("total", "subtotal", "tax", "service")
# name, extractor folder, OCR folder, grounding on?, expected total (correct, wrong, no_answer)
PIPES = [
    ("rules_easyocr", "cache/extract_rules", "cache/ocr", False,
     {"validation": (66, 16, 16), "test": (54, 14, 27)}),
    ("llm_easyocr", "cache/llm_groq", "cache/ocr", True,
     {"validation": (65, 13, 20), "test": (54, 11, 30)}),
    ("rules_paddle", "cache/extract_rules_v3_both", "cache/ocr_paddle", False,
     {"validation": (90, 5, 3), "test": (74, 5, 16)}),
    ("llm_paddle", "cache/llm_groq_paddle", "cache/ocr_paddle", True,
     {"validation": (85, 6, 7), "test": (73, 0, 22)}),
]


def outcome(res, field):
    return res["fields"][field].get("outcome")


def group_of(res):
    outs = [outcome(res, f) for f in FIELDS]
    if "wrong" in outs:
        return "error"
    if "no_answer" in outs:
        return "missing"
    return "ok"


def score_cash_change(labels, texts, split):
    """How good is the cash/change finder against CORD's cashprice / changeprice labels?"""
    tally = {k: Counter() for k in ("cash", "change")}
    wrong_idx = {k: [] for k in tally}
    for i, raw in enumerate(labels):
        total = json.loads(raw)["gt_parse"].get("total", {})
        if not isinstance(total, dict):
            continue
        found = find_cash_change(texts[i], CURRENCY)
        for key, label_key in (("cash", "cashprice"), ("change", "changeprice")):
            raw_label = total.get(label_key)
            label = try_parse(str(raw_label)) if raw_label is not None else None
            got = found[key]
            if label is None:
                tally[key]["extra" if got is not None else "no label, none found"] += 1
                continue
            tally[key]["label present"] += 1
            if got is None:
                tally[key]["not found"] += 1
            elif got == label:
                tally[key]["correct"] += 1
            else:
                tally[key]["wrong"] += 1
                wrong_idx[key].append(i)
    return tally, wrong_idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["validation", "test", "train"], required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--pipes", nargs="*", default=None)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    split = args.split
    if split == "train" and args.limit is None:
        ap.error("--limit is required for train")
    pipes = [p for p in PIPES if args.pipes is None or p[0] in args.pipes]
    show_idx = split == "validation"  # indices are printed on validation only

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    if split == "test":
        check_test_set(ds)
    labels = list(ds["ground_truth"])[:args.limit]

    texts = {}
    for ocr in sorted({p[2] for p in pipes}):
        texts[ocr] = []
        for i in range(len(labels)):
            pieces = json.loads(Path(ocr, f"{split}_{i:03d}.json").read_text(encoding="utf-8"))["pieces"]
            texts[ocr].append(render_receipt(pieces, CURRENCY))

    summary = {"split": split, "tolerance": str(TOLERANCE), "pipelines": {}}
    error_by_receipt = defaultdict(dict)  # receipt -> {pipeline: flagged?}

    for name, folder, ocr, grounding, expect in pipes:
        rows = []
        for i, raw in enumerate(labels):
            rec = json.loads(Path(folder, f"{split}_{i:03d}.json").read_text(encoding="utf-8"))
            res = score_receipt(json.loads(raw)["gt_parse"], rec, CURRENCY)
            out = validate(rec, tolerance=TOLERANCE, text=texts[ocr][i],
                           currency=CURRENCY, grounding=grounding)
            codes = {f["code"] for f in out["flags"]}
            rows.append({"i": i, "res": res, "g": group_of(res), "out": out, "codes": codes,
                         "value": bool(codes & VALUE_CODES), "queue": out["review"]})

        n = len(rows)
        print("=" * 72)
        print(f"{name}   ({split}, tolerance {TOLERANCE})")
        tc = Counter(outcome(r["res"], "total") for r in rows)
        got = (tc["correct"], tc["wrong"], tc["no_answer"])
        if split in expect:
            print(f"  sanity: total correct/wrong/no_answer = {got}  expected {expect[split]}  "
                  f"{'MATCH' if got == expect[split] else 'MISMATCH  <-- STOP, do not use these numbers'}")
        else:
            print(f"  scorer counts (no frozen expectation for {split}): "
                  f"total correct/wrong/no_answer = {got}")

        members = {g: [r for r in rows if r["g"] == g] for g in ("error", "missing", "ok")}
        err, mis, ok = members["error"], members["missing"], members["ok"]
        flagged_all = sum(r["out"]["flagged"] for r in err)
        flagged_val = sum(r["value"] for r in err)
        false_alarms = sum(r["out"]["flagged"] for r in ok)
        mis_flagged = sum(r["out"]["flagged"] for r in mis)
        mis_value = sum(r["value"] for r in mis)
        review = sum(r["out"]["flagged"] for r in rows)
        false_alarms_val = sum(r["value"] for r in ok)
        review_val = sum(r["value"] for r in rows)

        print(f"  groups: error {len(err)}, missing {len(mis)}, ok {len(ok)}")
        q_err = sum(r["queue"] for r in err)
        q_ok = sum(r["queue"] for r in ok)
        q_mis = sum(r["queue"] for r in mis)
        q_all = sum(r["queue"] for r in rows)
        print(f"  QUEUE (decision 6b)  error records in the review queue:        {q_err} of {len(err)}")
        print(f"                       clean records in the queue (false alarms): {q_ok} of {len(ok)}")
        print(f"                       missing-field records in the queue:        {q_mis} of {len(mis)}")
        print(f"                       review rate (queue / all receipts):        {q_all} of {n}")
        print("  strict variants (all flags, then value-based only) follow:")
        print(f"  strict    error records flagged (any check):        {flagged_all} of {len(err)}")
        print(f"            error records flagged (value-based checks): {flagged_val} of {len(err)}")
        print(f"  false alarms (ok records flagged):                    {false_alarms} of {len(ok)}")
        print(f"  review rate (all receipts flagged):                   {review} of {n}")
        print(f"  value-based only: false alarms {false_alarms_val} of {len(ok)}, "
              f"review rate {review_val} of {n}")
        print(f"  missing-field records flagged (any / value-based):    {mis_flagged} / {mis_value} of {len(mis)}")

        print("  records carrying each flag code:")
        table = defaultdict(Counter)
        for r in rows:
            for c in r["codes"]:
                table[c][r["g"]] += 1
        for c in sorted(table):
            t = table[c]
            kind = "value" if c in VALUE_CODES else "other"
            print(f"    {c:22} {kind:5}  error {t['error']:3}  ok {t['ok']:3}  missing {t['missing']:3}")

        ran = Counter()
        for r in rows:
            for k in r["out"]["evaluated"]:
                ran[k] += 1
        print("  checks that could run on N receipts:", dict(ran))

        if show_idx:
            print("  error records NOT in the review queue:", [r["i"] for r in err if not r["queue"]])
            print("  error records NOT flagged by any check:", [r["i"] for r in err if not r["out"]["flagged"]])
            print("  error records NOT flagged by a value-based check:",
                  [r["i"] for r in err if not r["value"]])

        for r in err:
            error_by_receipt[r["i"]][name] = r["queue"]
        summary["pipelines"][name] = {
            "total_correct_wrong_noanswer": list(got),
            "error": len(err), "missing": len(mis), "ok": len(ok),
            "error_flagged_any": flagged_all, "error_flagged_value": flagged_val,
            "false_alarms": false_alarms, "review": review, "receipts": n,
            "false_alarms_value": false_alarms_val, "review_value": review_val,
            "queue_error": q_err, "queue_false_alarms": q_ok,
            "queue_missing": q_mis, "queue_review": q_all,
            "missing_flagged_any": mis_flagged, "missing_flagged_value": mis_value,
            "codes": {c: dict(t) for c, t in table.items()},
            "could_run": dict(ran),
        }

    print("=" * 72)
    pairs = sum(len(v) for v in error_by_receipt.values())
    pairs_caught = sum(sum(v.values()) for v in error_by_receipt.values())
    distinct = len(error_by_receipt)
    all_caught = sum(all(v.values()) for v in error_by_receipt.values())
    print("POOLED over the four pipelines (review-queue flags):")
    print(f"  error records, pipeline by pipeline (same receipt counted per pipeline): {pairs_caught} of {pairs} flagged")
    print(f"  DISTINCT receipts that are an error record in at least one pipeline: {distinct}")
    print(f"  of those, flagged in EVERY pipeline where they are an error: {all_caught}")
    summary["pooled"] = {"pairs": pairs, "pairs_flagged": pairs_caught,
                         "distinct_receipts": distinct, "flagged_in_every_pipeline": all_caught}

    if split == "validation":
        print("=" * 72)
        print("CASH / CHANGE FINDER vs CORD labels (validation only)")
        for label, ocr in (("EasyOCR text", "cache/ocr"), ("Paddle text", "cache/ocr_paddle")):
            tally, wrong_idx = score_cash_change(labels, texts[ocr], split)
            for key in ("cash", "change"):
                t = tally[key]
                print(f"  {label:13} {key:7} label present {t['label present']:3}: "
                      f"correct {t['correct']:3}, wrong {t['wrong']:3}, not found {t['not found']:3}; "
                      f"extra (finder answered, no label) {t['extra']}")
                print(f"{'':24}wrong on: {wrong_idx[key]}")

    out_dir = Path("cache/scores")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{split}_validator{args.tag}.json").write_text(
        json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"\nsummary (counts only) saved to cache/scores/{split}_validator{args.tag}.json")


if __name__ == "__main__":
    main()
