import time
import numpy as np
import easyocr
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
image = ds[0]["image"].convert("RGB")
image.save("results/inspect/val_0.png")

reader = easyocr.Reader(["en"], gpu=False)

t0 = time.time()
results = reader.readtext(np.array(image))
print(f"{len(results)} pieces in {time.time() - t0:.1f}s")

for box, text, conf in results:
    x, y = box[0]
    print(f"{conf:.2f}  y={int(y):4d}  x={int(x):4d}  {text}")