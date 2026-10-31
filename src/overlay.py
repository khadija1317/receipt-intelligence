"""Draw OCR boxes on a receipt photo, coloured by the OCR's own confidence.

Confidence is how sure the OCR engine was about a piece. It is not accuracy:
the project has a real case of a wrong piece read with confidence 1.00.
"""
from PIL import ImageDraw

GREEN = (0, 160, 0)
ORANGE = (255, 140, 0)
RED = (220, 0, 0)
HIGH = 0.8  # same thresholds as scripts/side_by_side.py
LOW = 0.4


def conf_color(conf):
    if conf >= HIGH:
        return GREEN
    if conf >= LOW:
        return ORANGE
    return RED


def draw_boxes(image, pieces):
    """Return a copy of the image with one outlined box per OCR piece."""
    canvas = image.convert("RGB")  # a new image, the original is not touched
    draw = ImageDraw.Draw(canvas)
    width = max(2, canvas.size[0] // 250)
    for p in pieces:
        pts = [tuple(pt) for pt in p["box"]]
        draw.line(pts + [pts[0]], fill=conf_color(p["conf"]), width=width)
    return canvas
