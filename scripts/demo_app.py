"""Upload-and-review page for the receipt pipeline (rules arm only).

Run from the repo root, in .venv:  python -m scripts.demo_app
OCR runs in the separate paddle venv (see src/pipeline.py); everything after OCR runs here.
"""
import threading
import traceback

import gradio as gr
from PIL import Image, ImageOps

from src import display
from src.overlay import draw_boxes
from src.pipeline import load_example, run_ocr, run_stages

INTRO = (
    "# Receipt Intelligence\n"
    "Receipt photo → OCR (PaddleOCR) → merge → repair → rules extractor → validator.\n\n"
    "The validator's job is to flag records that cannot be trusted. "
    "It never sees the image, only the numbers the pipeline extracted.\n\n"
)
OCR_NOTE = (
    "Each box is one piece of text the OCR found. Green: confidence 0.8 or higher. "
    "Orange: 0.4 to 0.8. Red: below 0.4. "
    "Confidence is how sure the engine was about a piece, not whether the piece is right: "
    "a wrong piece can be green."
)
MERGE_NOTE = (
    "Pieces on the same row are grouped, then two neighbouring pieces that look like the two halves "
    "of one amount are joined. Joined pieces are shown in { }."
)
REPAIR_NOTE = (
    "Every amount-shaped piece, as the repair step saw it. ok: read as it was. "
    "repaired: a known OCR slip was fixed. review: could not be read safely."
)
EXTRACT_NOTE = (
    "The rules extractor (v3) finds the total, subtotal, tax and service by keyword lines, "
    "and takes everything above the first of them as items. "
    "This is the text the validator read (the same text the measured pipeline used):"
)
VALIDATE_NOTE = (
    "Tolerance: 1 rupiah. A check that cannot run is never counted as a pass. "
    "The reasons for review and the notes are listed in the banner at the top."
)
TIMING_NOTE = (
    "OCR times come from the OCR process. The stages after OCR take milliseconds."
)

EXAMPLES = (
    ("validation_000", "Example 1: passes the checks"),
    ("validation_016", "Example 2: caught (amounts one row off)"),
    ("validation_066", "Example 3: total could not be read"),
    ("validation_007", "Example 4: queued although the total is right"),
)
EXAMPLES_NOTE = (
    "**Examples** (CORD validation receipts). An example loads a saved OCR result, so there is "
    "no wait. Every later stage runs live. These receipts were used while the pipeline was "
    "being developed, so they show how it behaves, not how well it performs. The numbers in the "
    "verdict come from other receipts."
)

_OCR_LOCK = threading.Lock()


def _no_result(message):
    return (display.failure_html(message), [], [], None, "", [], [], "", [], [])


def process(image_path, cached_ocr=None):
    if not image_path:
        return _no_result("Upload a receipt image first.")
    try:
        if cached_ocr is None:
            with _OCR_LOCK:
                ocr = run_ocr(image_path)
        else:
            ocr = cached_ocr
        if not ocr["ok"]:
            return _no_result(ocr["message"])
        record = ocr["record"]
        pieces = record["pieces"]
        result = run_stages(pieces)

        with Image.open(image_path) as raw:
            photo = ImageOps.exif_transpose(raw).convert("RGB")  # same rule as scripts/ocr_one_image
        boxed = draw_boxes(photo, pieces)

        source = ocr.get("source", "live")
        side = record.get("detector_side_used")
        summary = (f"{len(pieces)} pieces found. "
                   + (f"Detector size used: {side} px. " if side else "")
                   + f"Image size read: {record['image_size'][0]} × {record['image_size'][1]} px.")
        if source == "cache":
            summary += (" **OCR result loaded from a saved file: the OCR did not run for this "
                        "example. Every later stage ran live.**")
        timing = display.timing_rows(
            result["seconds"], ocr_seconds=record["seconds"],
            ocr_load_seconds=record.get("load_seconds"), ocr_wall_seconds=ocr["wall_seconds"],
            ocr_source=source)
        return (
            display.verdict_html(result["verdict"], result["checks"]),
            display.fields_rows(result["record"]),
            display.items_rows(result["record"]),
            boxed,
            summary,
            display.merge_rows(result["merge"]),
            display.repair_rows(result["repair"]),
            result["text"],
            display.check_rows(result["checks"]),
            timing,
        )
    except Exception:
        traceback.print_exc()
        return _no_result("Something went wrong while processing this image (details are in the console).")


def example_handler(stem):
    def handler():
        example = load_example(stem)
        if example is None:
            return (None,) + _no_result("The example files were not found in demo_examples/.")
        return (example["image_path"],) + process(example["image_path"], example["ocr"])
    return handler


def table(label, headers):
    return gr.Dataframe(headers=headers, interactive=False, wrap=True, label=label)


with gr.Blocks(title="Receipt Intelligence", analytics_enabled=False) as demo:
    gr.Markdown(INTRO)
    with gr.Row():
        with gr.Column(scale=1, min_width=320):
            upload = gr.Image(type="filepath", sources=["upload"], label="Receipt photo", height=520)
            run = gr.Button("Check this receipt", variant="primary")
            gr.Markdown(EXAMPLES_NOTE)
            example_buttons = [(stem, gr.Button(label)) for stem, label in EXAMPLES]
        with gr.Column(scale=1, min_width=360):
            banner = gr.HTML("<div style='padding:14px;opacity:0.7;'>"
                             "Upload a receipt photo and press the button.</div>")
            gr.Markdown("### What was extracted")
            fields = table("Fields", display.FIELD_HEADERS)
            items = table("Items", display.ITEM_HEADERS)
            with gr.Accordion("Behind the scenes, step by step", open=False):
                with gr.Accordion("1. OCR: what the engine found", open=False):
                    gr.Markdown(OCR_NOTE)
                    boxed = gr.Image(type="pil", interactive=False, label="OCR boxes")
                    ocr_summary = gr.Markdown("")
                with gr.Accordion("2. Merge: pieces into lines", open=False):
                    gr.Markdown(MERGE_NOTE)
                    merge = table("Rows", display.MERGE_HEADERS)
                with gr.Accordion("3. Repair: amount-shaped pieces", open=False):
                    gr.Markdown(REPAIR_NOTE)
                    repair = table("Amounts", display.REPAIR_HEADERS)
                with gr.Accordion("4. Extractor: the text it worked from", open=False):
                    gr.Markdown(EXTRACT_NOTE)
                    text = gr.Textbox(lines=12, interactive=False, label="Merged and repaired text")
                with gr.Accordion("5. Validator: the three arithmetic checks", open=False):
                    gr.Markdown(VALIDATE_NOTE)
                    checks = table("Checks", display.CHECK_HEADERS)
                with gr.Accordion("6. Time per stage", open=False):
                    gr.Markdown(TIMING_NOTE)
                    timing = table("Timing", display.TIMING_HEADERS)

    results = [banner, fields, items, boxed, ocr_summary, merge, repair, text, checks, timing]
    run.click(process, inputs=upload, outputs=results)
    for stem, button in example_buttons:
        button.click(example_handler(stem), inputs=None, outputs=[upload] + results)

if __name__ == "__main__":
    demo.launch(inbrowser=True)
