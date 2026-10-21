import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset

from scripts.total_visible import try_parse

LLM = Path("cache/llm_groq")
RAW = Path("cache/llm_groq_raw")
RULES = Path("cache/extract_rules")


def outcome(result, label):
    """correct / wrong / null (no field) / review (field found, amount unreadable)."""
    field = result["total"]
    if field is None:
        return "null"
    if field["value"] is None:
        return "review"
    return "correct" if Decimal(field["value"]) == label else "wrong"


def visible(text, label):
    """APPROXIMATE: does the label value appear as ONE token in the text?
    Misses numbers split across tokens (like '18 , 181')."""
    for token in text.split():
        try:
            if try_parse(token) == label:
                return True
        except Exception:
            pass
    return False


def short(value, n=34):
    return (str(value) if value is not None else "-")[:n]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    table = Counter()
    failures = []
    for i, raw in enumerate(ds["ground_truth"]):
        gt = json.loads(raw)["gt_parse"]
        total = gt.get("total", {})
        label_text = total.get("total_price") if isinstance(total, dict) else None
        label = try_parse(str(label_text)) if label_text is not None else None
        if label is None:
            continue                      # not scored: no usable total label
        llm = json.loads((LLM / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        rules = json.loads((RULES / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        text = json.loads((RAW / f"validation_{i:03d}.json").read_text(encoding="utf-8"))["text"]
        o_llm, o_rules = outcome(llm, label), outcome(rules, label)
        # for the overlap table, 'null' and 'review' both mean "no answer"
        table[(o_llm if o_llm in ("correct", "wrong") else "no_answer",
               o_rules if o_rules in ("correct", "wrong") else "no_answer")] += 1
        if o_llm != "correct":
            f = llm["total"]
            failures.append((i, label, o_llm, o_rules, visible(text, label),
                             None if f is None else f["raw"],
                             None if f is None else f["line"]))

    print("OVERLAP (rows = LLM, columns = rules v2), counts of receipts\n")
    kinds = ("correct", "wrong", "no_answer")
    print(f"{'':12s}" + "".join(f"{k:>12s}" for k in kinds))
    for a in kinds:
        print(f"{a:12s}" + "".join(f"{table[(a, b)]:12d}" for b in kinds))

    seen = [f for f in failures if f[4]]
    print(f"\nLLM failures: {len(failures)}; label value visible in the LLM's text "
          f"(approximate): {len(seen)}; not visible: {len(failures) - len(seen)}")
    print("\nEVERY LLM FAILURE")
    print("idx   label       llm     rules   seen  llm_raw                 evidence line")
    for i, label, o_llm, o_rules, seen_, raw, line in failures:
        print(f"{i:3d}   {str(label):10s}  {o_llm:7s} {o_rules:7s} {'yes' if seen_ else 'no':4s}  "
              f"{short(raw, 22):22s}  {short(line)}")

    print("\nCORRECT but suspicious: payment-row receipts 41 and 94")
    for i in (41, 94):
        llm = json.loads((LLM / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        f = llm["total"]
        print(f"  val {i}: " + ("no total" if f is None else f"{f['raw']!r}  line={f['line']!r}"))


if __name__ == "__main__":
    main()