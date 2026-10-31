"""Draw the Day 8 error-analysis sample from holdout B (CORD train 0-399).

Rules v3 "both" on Paddle text, frozen validator. Selection rule: docs/results_notes.md,
"Day 8 - Decisions 10 and 11" (seed 42, run once, no redraw).

Run (.venv): python -m scripts.draw_sample
"""
import json
import random
import sys
from pathlib import Path

from datasets import load_dataset

from scripts.run_validate import CURRENCY, TOLERANCE, group_of, outcome
from src.llm_extract import render_receipt
from src.score import score_receipt
from src.validate import validate

N = 400
SEED = 42
OCR_DIR = "cache/ocr_paddle"
REC_DIR = "cache/extract_rules_v3_both"
OUT = Path("cache/scores/holdout_b_sample.json")
EXPECT = {"error": 24, "missing": 120, "ok": 256, "error_caught": 23, "error_missed": 1,
          "false_alarm": 50, "total_no_answer": 57}


def show(sample):
    w = sample["wrong_value"]
    print(f"seed {sample['seed']}")
    print(f"wrong-value, missed by the validator ({len(w['missed'])}): {w['missed']}")
    print(f"wrong-value, caught by the validator ({len(w['caught_sampled'])}): {w['caught_sampled']}")
    print(f"no total ({len(sample['no_total'])}): {sample['no_total']}")
    print(f"false alarm ({len(sample['false_alarm'])}): {sample['false_alarm']}")


def main():
    if OUT.exists():
        print(f"{OUT} already exists: the draw was done. Showing the saved sample, NOT redrawing.")
        show(json.loads(OUT.read_text(encoding="utf-8")))
        return

    ds = load_dataset("naver-clova-ix/cord-v2", split="train")
    labels = list(ds["ground_truth"])[:N]

    rows = []
    for i, raw in enumerate(labels):
        pieces = json.loads(Path(OCR_DIR, f"train_{i:03d}.json").read_text(encoding="utf-8"))["pieces"]
        text = render_receipt(pieces, CURRENCY)
        rec = json.loads(Path(REC_DIR, f"train_{i:03d}.json").read_text(encoding="utf-8"))
        res = score_receipt(json.loads(raw)["gt_parse"], rec, CURRENCY)
        out = validate(rec, tolerance=TOLERANCE, text=text, currency=CURRENCY, grounding=False)
        rows.append({"i": i, "g": group_of(res), "queue": bool(out["review"]),
                     "total_no_answer": outcome(res, "total") == "no_answer"})

    error = [r["i"] for r in rows if r["g"] == "error"]
    error_caught = [r["i"] for r in rows if r["g"] == "error" and r["queue"]]
    error_missed = [r["i"] for r in rows if r["g"] == "error" and not r["queue"]]
    missing_n = sum(r["g"] == "missing" for r in rows)
    ok_n = sum(r["g"] == "ok" for r in rows)
    total_na_all = [r["i"] for r in rows if r["total_no_answer"]]
    no_total = [i for i in total_na_all if i not in set(error)]  # precedence: wrong-value first
    false_alarm = [r["i"] for r in rows if r["g"] == "ok" and r["queue"]]

    got = {"error": len(error), "missing": missing_n, "ok": ok_n,
           "error_caught": len(error_caught), "error_missed": len(error_missed),
           "false_alarm": len(false_alarm), "total_no_answer": len(total_na_all)}
    print("pool sizes (counts only):")
    bad = False
    for k, want in EXPECT.items():
        flag = "MATCH" if got[k] == want else "MISMATCH"
        bad = bad or got[k] != want
        print(f"  {k:16} got {got[k]:4}  expected {want:4}  {flag}")
    print(f"  no-total pool AFTER precedence: {len(no_total)} (may be below 57; that is fine)")
    if bad:
        print("STOP: a pool size drifted from Day 7. Nothing drawn, nothing saved.")
        sys.exit(1)

    rng = random.Random(SEED)
    caught_sampled = sorted(rng.sample(sorted(error_caught), 7))
    no_total_sampled = sorted(rng.sample(sorted(no_total), 6))
    false_alarm_sampled = sorted(rng.sample(sorted(false_alarm), 6))
    sample = {"seed": SEED, "split": "train", "pipeline": "rules_paddle",
              "wrong_value": {"missed": sorted(error_missed), "caught_sampled": caught_sampled},
              "no_total": no_total_sampled, "false_alarm": false_alarm_sampled}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sample, indent=1), encoding="utf-8")
    print(f"\nDRAWN once and saved to {OUT}:")
    show(sample)


if __name__ == "__main__":
    main()
