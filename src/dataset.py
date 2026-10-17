import json, hashlib

def check_test_set(ds):
    with open("data/test_ids.json", encoding="utf-8") as f:
        saved = json.load(f)
    now = hashlib.sha256("".join(ds["ground_truth"]).encode("utf-8")).hexdigest()
    if now != saved["labels_sha256"]:
        raise RuntimeError("This is not the fixed test set (wrong split or changed data).")