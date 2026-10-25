"""Break the review queue down by cause. Measurement only: changes no check.

Run: python -m scripts.queue_breakdown --split validation   (prints indices)
     python -m scripts.queue_breakdown --split test         (counts only, POST-HOC)
"""
import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.run_validate import CURRENCY, PIPES, TOLERANCE, group_of, outcome
from scripts.total_visible import try_parse
from src.dataset import check_test_set
from src.llm_extract import render_receipt
from src.score import score_receipt
from src.validate import QUEUE_CODES, validate

ARITH = {"TOTAL_VS_BASE", "ITEMS_VS_SUBTOTAL"}
OTHER_FIELDS = ("subtotal", "tax", "service")


def label_prices(gt):
    """Top-level label item prices as a Counter of Decimals."""
    menu = gt.get("menu", [])
    menu = [menu] if isinstance(menu, dict) else menu
    prices = Counter()
    for m in menu:
        raw = m.get("price") if isinstance(m, dict) else None
        v = try_parse(str(raw)) if raw is not None else None
        if v is not None:
            prices[v] += 1
    return prices


def record_prices(rec):
    """Extracted item prices as a Counter, plus how many had no readable price."""
    prices = Counter()
    unreadable = 0
    for m in rec.get("menu") or []:
        p = m.get("price") or {}
        try:
            prices[Decimal(str(p["value"]))] += 1
        except Exception:
            unreadable += 1
    return prices, unreadable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["validation", "test"], required=True)
    split = ap.parse_args().split
    show = split == "validation"

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    if split == "test":
        check_test_set(ds)
        print("TEST SPLIT: counts only. This is a POST-HOC breakdown, not the frozen verdict.")
    labels = ds["ground_truth"]

    texts = {}
    for ocr in ("cache/ocr", "cache/ocr_paddle"):
        texts[ocr] = []
        for i in range(len(labels)):
            pieces = json.loads(Path(ocr, f"{split}_{i:03d}.json").read_text(encoding="utf-8"))["pieces"]
            texts[ocr].append(render_receipt(pieces, CURRENCY))

    for name, folder, ocr, grounding, _expect in PIPES:
        clean = {"label has no total": [], "items differ from label": [], "unexplained": []}
        miss = {"total itself unanswered": [], "total right, other field empty, arithmetic fired": [],
                "other": []}
        empty_fields = Counter()
        n_queue = 0
        for i, raw in enumerate(labels):
            rec = json.loads(Path(folder, f"{split}_{i:03d}.json").read_text(encoding="utf-8"))
            gt = json.loads(raw)["gt_parse"]
            res = score_receipt(gt, rec, CURRENCY)
            out = validate(rec, tolerance=TOLERANCE, text=texts[ocr][i],
                           currency=CURRENCY, grounding=grounding)
            if not out["review"]:
                continue
            n_queue += 1
            g = group_of(res)
            codes = sorted({f["code"] for f in out["flags"] if f["code"] in QUEUE_CODES})
            if g == "ok":
                lp = label_prices(gt)
                rp, unread = record_prices(rec)
                if outcome(res, "total") in ("not_scored", "extra"):
                    clean["label has no total"].append((i, codes))
                elif (lp != rp or unread) and (set(codes) & ARITH):
                    clean["items differ from label"].append((i, codes))
                else:
                    clean["unexplained"].append((i, codes))
            elif g == "missing":
                empties = [f for f in OTHER_FIELDS if outcome(res, f) == "no_answer"]
                if outcome(res, "total") == "no_answer":
                    miss["total itself unanswered"].append((i, codes))
                elif empties and (set(codes) & ARITH):
                    miss["total right, other field empty, arithmetic fired"].append((i, codes))
                    for f in empties:
                        empty_fields[f] += 1
                else:
                    miss["other"].append((i, codes))

        print("=" * 72)
        print(f"{name}   ({split}, tolerance {TOLERANCE})   receipts in the queue: {n_queue}")
        print("  CLEAN records in the queue (false alarms), by cause:")
        for k, v in clean.items():
            print(f"    {k:28} {len(v):3}")
            if show:
                for i, codes in v:
                    print(f"        val {i:3}: {codes}")
        print("  MISSING-FIELD records in the queue, by cause:")
        for k, v in miss.items():
            print(f"    {k:48} {len(v):3}")
            if show:
                for i, codes in v:
                    print(f"        val {i:3}: {codes}")
        print("  empty fields among 'total right, other field empty':", dict(empty_fields))


if __name__ == "__main__":
    main()
