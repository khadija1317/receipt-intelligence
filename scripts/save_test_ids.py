import json, hashlib
from pathlib import Path
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="test")

fingerprint = hashlib.sha256("".join(ds["ground_truth"]).encode("utf-8")).hexdigest()

record = {
    "dataset": "naver-clova-ix/cord-v2",
    "split": "test",
    "n": len(ds),
    "indices": list(range(len(ds))),
    "labels_sha256": fingerprint,
}

Path("data").mkdir(exist_ok=True)
Path("data/test_ids.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print("saved", record["n"], "ids; fingerprint", fingerprint[:12])