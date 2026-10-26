import argparse
import json
import statistics
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
from datasets import load_dataset
from paddleocr import PaddleOCR

import faulthandler

# If Paddle's native code ever kills the process, Python's own crash dump
# goes into this file instead of vanishing.
_crash_log = open("cache/paddle_crash.log", "a")
faulthandler.enable(file=_crash_log)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "validation", "train"], required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default="cache/ocr_paddle")
    parser.add_argument("--max-side", type=int, default=2560)
    args = parser.parse_args()
    split = args.split
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("naver-clova-ix/cord-v2", split=split)
    if split == "train":
        if args.limit is None:
            parser.error("--limit is required for train")
        n = min(args.limit, len(ds))
    else:
        assert len(ds) == 100, f"expected 100 {split} receipts, got {len(ds)}"
        n = len(ds)
    if split == "test":
        from src.dataset import check_test_set

        check_test_set(ds)

    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_det_limit_type="max",
        text_det_limit_side_len=args.max_side,
    )
    engine_version = (
        f"paddleocr {version('paddleocr')} + paddlepaddle {version('paddlepaddle')}"
        f" (detector max side {args.max_side})"
    )

    times = []
    total_pieces = 0
    done = 0
    fallbacks = 0
    failed = 0
    for i in range(n):
        path = out / f"{split}_{i:03d}.json"
        if path.exists():
            continue

        image = ds[i]["image"].convert("RGB")
        bgr = np.ascontiguousarray(np.array(image)[:, :, ::-1])
        t0 = time.time()
        result = None
        used_side = args.max_side
        for side in (args.max_side, 1600, 1280):
            try:
                result = ocr.predict(
                    bgr, text_det_limit_type="max", text_det_limit_side_len=side
                )[0]
                used_side = side
                break
            except RuntimeError:
                continue
        seconds = time.time() - t0
        if result is None:
            failed += 1
            continue
        if used_side != args.max_side:
            fallbacks += 1
        if done == 0:
            print("detector settings:", result["text_det_params"])

        pieces = [
            {
                "box": [[int(x), int(y)] for x, y in np.array(poly).tolist()],
                "text": str(text),
                "conf": round(float(score), 4),
            }
            for text, score, poly in zip(
                result["rec_texts"], result["rec_scores"], result["rec_polys"]
            )
        ]
        record = {
            "index": i,
            "image_size": list(image.size),
            "engine": "paddleocr",
            "engine_version": engine_version.replace(f"max side {args.max_side}", f"max side {used_side}"),
            "languages": ["en"],
            "seconds": round(seconds, 2),
            "pieces": pieces,
        }

        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

        times.append(seconds)
        total_pieces += len(pieces)
        done += 1
        if split == "validation":
            print(f"{i:3d}  {len(pieces):3d} pieces  {seconds:4.1f}s")
        elif done % 10 == 0:
            print(f"{done} receipts done this run")

    if times:
        print(
            f"\nthis run: {len(times)} receipts, {total_pieces} pieces, "
            f"median {statistics.median(times):.1f}s, max {max(times):.1f}s, "
            f"total {sum(times) / 60:.1f} min"
        )
    else:
        print("nothing to do: all files already exist")
    print(f"detector fallbacks this run: {fallbacks}, failed outright: {failed}")


if __name__ == "__main__":
    main()
