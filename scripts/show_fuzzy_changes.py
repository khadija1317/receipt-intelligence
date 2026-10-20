"""Which validation lines does the fuzzy keyword rule newly classify?
Run: python -m scripts.show_fuzzy_changes
"""
import json
from collections import Counter
from pathlib import Path

from src.extract_rules import classify, classify_fuzzy, line_parts
from src.merge import merge_receipt

OCR = Path("cache/ocr")


def main():
    kinds = Counter()
    receipts = set()
    for i in range(100):
        record = json.loads((OCR / f"validation_{i:03d}.json").read_text(encoding="utf-8"))
        for line in merge_receipt(record["pieces"]):
            label, _ = line_parts(line, "IDR")
            if classify(label) is not None:
                continue  # v1 already handled it
            kind = classify_fuzzy(label)
            if kind:
                kinds[kind] += 1
                receipts.add(i)
                print(f"val {i:3d}  {kind:9}  line: {line['text'][:50]}")
    print(f"\nnewly classified lines: {dict(kinds)}, in {len(receipts)} receipts")


if __name__ == "__main__":
    main()