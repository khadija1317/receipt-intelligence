"""OCR one image with PaddleOCR and save the raw pieces in the cache format.

Usage: python -m scripts.ocr_one_image --image receipt.jpg --out result.json
Exit code 0: the file was written. Exit code 3: every detector size failed.
"""
import argparse
import faulthandler
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from paddleocr import PaddleOCR

Path("cache").mkdir(exist_ok=True)
_crash_log = open("cache/paddle_crash.log", "a")
faulthandler.enable(file=_crash_log)

FALLBACK_SIDES = (1600, 1280)  # same chain as scripts.run_ocr_paddle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-side", type=int, default=2560)
    args = parser.parse_args()

    # Phone photos carry a rotation flag that PIL ignores unless told.
    image = ImageOps.exif_transpose(Image.open(args.image)).convert("RGB")
    bgr = np.ascontiguousarray(np.array(image)[:, :, ::-1])

    t_load = time.time()
    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_det_limit_type="max",
        text_det_limit_side_len=args.max_side,
    )
    load_seconds = time.time() - t_load

    sides = [args.max_side] + [s for s in FALLBACK_SIDES if s < args.max_side]
    result = None
    used_side = None
    t0 = time.time()
    for side in sides:
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
        print("OCR failed at every detector size")
        sys.exit(3)

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
        "index": None,
        "image_size": list(image.size),
        "engine": "paddleocr",
        "engine_version": f"paddleocr {version('paddleocr')} + paddlepaddle "
                          f"{version('paddlepaddle')} (detector max side {used_side})",
        "languages": ["en"],
        "seconds": round(seconds, 2),
        "load_seconds": round(load_seconds, 2),
        "detector_side_used": used_side,
        "pieces": pieces,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)
    print(f"{len(pieces)} pieces, {seconds:.1f}s")


if __name__ == "__main__":
    main()
