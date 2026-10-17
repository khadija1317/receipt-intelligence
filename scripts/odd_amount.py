import json, re
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
common = {"9.9", "9", "9,9"}

for i in range(len(ds)):
    total = json.loads(ds[i]["ground_truth"])["gt_parse"].get("total", {})
    tp = total.get("total_price") if isinstance(total, dict) else None
    if not tp:
        print(i, "NO total_price; total keys:", list(total.keys()) if isinstance(total, dict) else total)
    elif re.sub(r"\d+", "9", tp) not in common:
        print(i, repr(tp))