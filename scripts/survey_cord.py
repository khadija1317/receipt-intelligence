import json, re
from collections import Counter
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="test")

top_keys, menu_types = Counter(), Counter()
total_keys, sub_total_keys, shapes = Counter(), Counter(), Counter()




for i in range(len(ds)):
    gt = json.loads(ds[i]["ground_truth"])["gt_parse"]
    top_keys.update(gt.keys())
    menu_types[type(gt.get("menu")).__name__] += 1

    total = gt.get("total", {})
    if isinstance(total, dict):
        total_keys.update(total.keys())
        tp = total.get("total_price")
        if tp:
            shapes[re.sub(r"\d+", "9", tp)] += 1   # "60.000" -> "9.9", "82,000" -> "9,9"

    sub = gt.get("sub_total", {})
    if isinstance(sub, dict):
        sub_total_keys.update(sub.keys())

print("top-level keys:", dict(top_keys))
print("menu types:", dict(menu_types))
print("total keys:", dict(total_keys))
print("sub_total keys:", dict(sub_total_keys))
print("total_price shapes:", dict(shapes))

full = json.loads(ds[0]["ground_truth"])
print("\nvalid_line sample:")
print(json.dumps(full["valid_line"][:2], indent=2, ensure_ascii=False))