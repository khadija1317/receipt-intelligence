import argparse
import json
import time
from pathlib import Path

import easyocr
import numpy as np
from datasets import load_dataset

from src.dataset import check_test_set

OUT = Path("cache/ocr")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "validation"], default="test")
    args = parser.parse_args()
    split = args.split

    OUT.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    assert len(ds) == 100, f"expected 100 {split} receipts, got {len(ds)}"
    if split == "test":
        check_test_set(ds)

    reader = easyocr.Reader(["en"], gpu=False)

    for i in range(len(ds)):
        path = OUT / f"{split}_{i:03d}.json"
        if path.exists():
            continue

        image = ds[i]["image"].convert("RGB")
        t0 = time.time()
        results = reader.readtext(np.array(image))
        seconds = time.time() - t0

        record = {
            "index": i,
            "image_size": list(image.size),
            "engine": "easyocr",
            "engine_version": easyocr.__version__,
            "languages": ["en"],
            "seconds": round(seconds, 2),
            "pieces": [
                {
                    "box": [[int(x), int(y)] for x, y in box],
                    "text": text,
                    "conf": round(float(conf), 4),
                }
                for box, text, conf in results
            ],
        }

        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        print(f"{i:3d}  {len(results):3d} pieces  {seconds:4.1f}s")


if __name__ == "__main__":
    main()