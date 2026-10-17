import json
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="test")
print(ds)
print("rows:", len(ds))
print("columns:", ds.column_names)

for i in range(3):
    gt = json.loads(ds[i]["ground_truth"])   
    print(type(gt))
    print(gt.keys())
    print("\n--- receipt", i, "image size:", ds[i]["image"].size)
    print(json.dumps(gt["gt_parse"], indent=2, ensure_ascii=False))