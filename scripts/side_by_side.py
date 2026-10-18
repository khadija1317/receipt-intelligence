import argparse
import json
import random
from decimal import Decimal
from pathlib import Path

from datasets import load_dataset
from PIL import ImageDraw

from scripts.total_visible import try_parse
from src.extract_rules import extract_receipt
from src.geometry import group_rows
from src.merge import merge_receipt

SPLIT = "validation"  # hard-coded: this script never touches test
CURRENCY = "IDR"
CACHE = Path("cache/ocr")


def label_total(gt):
    total = gt.get("total", {})
    text = total.get("total_price") if isinstance(total, dict) else None
    return None if text is None else try_parse(str(text))


def total_is_wrong(pieces, gt):
    target = label_total(gt)
    if target is None:
        return False
    got = extract_receipt(pieces, CURRENCY)["total"]
    return got is None or got["value"] is None or Decimal(got["value"]) != target


def print_label(gt):
    menu = gt.get("menu", [])
    menu = [menu] if isinstance(menu, dict) else menu
    for m in menu:
        subs = f"  (+{len(m['sub'])} sub-items, ignored)" if "sub" in m else ""
        print(f"  item: {m.get('nm')!r}  cnt={m.get('cnt')}  price={m.get('price')}{subs}")
    print("  sub_total:", gt.get("sub_total"))
    print("  total:    ", gt.get("total"))


def print_ocr(pieces):
    for row, line in zip(group_rows(pieces), merge_receipt(pieces)):
        raw = "  ".join(f"{b['text']}[{b['conf']:.2f}]" for b in row)
        merged = " ".join("{" + t["text"] + "}" if t["joined"] else t["text"]
                          for t in line["tokens"])
        print(f"  raw   : {raw}")
        print(f"  merged: {merged}\n")


def print_extraction(result):
    for m in result["menu"]:
        p = m["price"]
        print(f"  item: {m['nm']!r}  cnt={m['cnt']}  price={p['value']} ({p['status']})")
    for key in ("subtotal", "service", "tax", "total"):
        f = result[key]
        text = "MISSING" if f is None else f"{f['value']} ({f['status']})  from line {f['line']!r}"
        print(f"  {key:9s}: {text}")
    print("  notes:", result["notes"])


def show_image(image, pieces):
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    width = max(2, image.size[0] // 250)
    for p in pieces:
        color = "green" if p["conf"] >= 0.8 else "orange" if p["conf"] >= 0.4 else "red"
        pts = [tuple(pt) for pt in p["box"]]
        draw.line(pts + [pts[0]], fill=color, width=width)
    image.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, help="show this receipt")
    parser.add_argument("--miss", action="store_true",
                        help="pick randomly among receipts whose extracted total is wrong")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    ds = load_dataset("naver-clova-ix/cord-v2", split=SPLIT)
    gts = [json.loads(r)["gt_parse"] for r in ds["ground_truth"]]
    pieces_of = lambda i: json.loads(
        (CACHE / f"{SPLIT}_{i:03d}.json").read_text(encoding="utf-8"))["pieces"]

    rng = random.Random(args.seed)
    if args.index is not None:
        i = args.index
    elif args.miss:
        wrong = [k for k in range(len(gts)) if total_is_wrong(pieces_of(k), gts[k])]
        print(f"{len(wrong)} validation receipts have a wrong or missing extracted total")
        i = rng.choice(wrong)
    else:
        i = rng.randrange(len(gts))

    pieces = pieces_of(i)
    print(f"\n##### validation receipt {i}   (rerun with --index {i} to see it again)")
    print("\n--- LABEL (what CORD says) ---")
    print_label(gts[i])
    print("\n--- EASYOCR, row by row (raw pieces with confidence, then merged) ---")
    print_ocr(pieces)
    print("--- EXTRACTOR OUTPUT ---")
    print_extraction(extract_receipt(pieces, CURRENCY))
    show_image(ds[i]["image"], pieces)


if __name__ == "__main__":
    main()