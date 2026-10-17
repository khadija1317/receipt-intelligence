import json
from pathlib import Path
from datasets import load_dataset

SPLIT = "test"
INDICES = [0, 9, 17, 21, 43, 47, 67, 70]
OUT = Path("results/inspect")

OUT.mkdir(parents=True, exist_ok=True)
ds = load_dataset("naver-clova-ix/cord-v2", split=SPLIT)

for i in INDICES:
    row = ds[i]
    gt = json.loads(row["ground_truth"])["gt_parse"]

    path = OUT / f"{SPLIT}_{i}.png"
    row["image"].save(path)

    print(f"\n=== receipt {i} -> {path}")
    print("sub_total:", gt.get("sub_total"))
    print("total:    ", gt.get("total"))