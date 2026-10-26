import argparse
import hashlib
import json
import sys
import time
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from groq import APIError, BadRequestError, Groq, RateLimitError

from src.dataset import check_test_set
from src.llm_extract import (FIELDS, MODEL, PROMPTS, SCHEMA, SYSTEM_PROMPT,
                             answer_to_result, build_messages, parse_reply,
                             render_receipt)

CURRENCY = "IDR"
OCR = Path("cache/ocr")
N_RECEIPTS = 100
TPM_BUDGET = 7000          # the free limit is 8,000 tokens per minute; keep a margin
MAX_REPLY_TOKENS = 3000    # a cap, so one receipt cannot burn the whole budget
def prompt_hash(prompt):
    return hashlib.md5(
        (prompt + json.dumps(SCHEMA, sort_keys=True)).encode("utf-8")).hexdigest()[:8]


PROMPT_HASH = prompt_hash(SYSTEM_PROMPT)


class DailyLimit(Exception):
    """Groq told us to wait a long time: the daily token cap is probably used up."""


class Pacer:
    """Keeps tokens-per-minute under budget by sleeping when needed."""

    def __init__(self, limit=TPM_BUDGET, window=60.0):
        self.limit, self.window = limit, window
        self.events = deque()   # (time, tokens used)

    def wait(self, estimate):
        while True:
            now = time.time()
            while self.events and now - self.events[0][0] >= self.window:
                self.events.popleft()
            used = sum(tokens for _, tokens in self.events)
            if not self.events or used + estimate <= self.limit:
                return
            time.sleep(max(self.window - (now - self.events[0][0]) + 0.2, 0.2))

    def record(self, tokens):
        self.events.append((time.time(), tokens))


def call_groq(client, text):
    """One call. Returns (reply text, finish reason, usage dict, seconds)."""
    for _ in range(5):
        started = time.time()
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=build_messages(text, SYSTEM_PROMPT),
                temperature=0,
                reasoning_effort="low",
                max_completion_tokens=MAX_REPLY_TOKENS,
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "receipt", "strict": True,
                                                 "schema": SCHEMA}},
            )
        except RateLimitError as err:
            try:
                wait = float(err.response.headers.get("retry-after", 20))
            except (TypeError, ValueError):
                wait = 20.0
            if wait > 120:
                raise DailyLimit(f"Groq asked us to wait {wait:.0f} s")
            print(f"  rate limited, waiting {wait:.0f} s")
            time.sleep(wait + 1)
            continue
        details = getattr(resp.usage, "completion_tokens_details", None)
        usage = {
            "prompt": resp.usage.prompt_tokens,
            "completion": resp.usage.completion_tokens,
            "total": resp.usage.total_tokens,
            "reasoning": getattr(details, "reasoning_tokens", None),
        }
        choice = resp.choices[0]
        return choice.message.content, choice.finish_reason, usage, time.time() - started
    raise APIError("still rate limited after 5 tries", request=None, body=None)


def show_trial(index, text, raw, result):
    """Validation only: everything about one receipt, side by side."""
    print(f"\n=== validation {index}")
    print("--- text the LLM read:")
    print(text)
    print("--- raw reply:")
    print(raw["reply"])
    print("--- parsed:")
    for item in result["menu"]:
        price = item["price"]
        print(f"  item: {item['nm']!r} cnt={item['cnt']} price={price['value']} "
              f"({price['status']}) raw={price['raw']!r}")
    for kind in FIELDS:
        f = result[kind]
        print(f"  {kind:9s}: " + ("MISSING" if f is None else
              f"{f['value']} ({f['status']}) raw={f['raw']!r} line={f['line']!r}"))
    u = raw["usage"]
    print(f"  tokens: {u['total']} (prompt {u['prompt']}, completion {u['completion']}, "
          f"reasoning {u['reasoning']}), {raw['seconds']:.1f} s, finish={raw['finish_reason']}")


def main():
    global SYSTEM_PROMPT, PROMPT_HASH
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "validation", "train"], default="validation")
    parser.add_argument("--limit", type=int, default=None,
                        help="how many receipts from the start (required for train)")
    parser.add_argument("--name", default="llm_groq",
                        help="folder name: raw replies go to cache/<name>_raw, parsed to cache/<name>")
    parser.add_argument("--only", type=int, nargs="*", help="receipt numbers (validation only)")
    parser.add_argument("--reparse", action="store_true",
                        help="rebuild parsed files from saved raw replies; no Groq calls")
    parser.add_argument("--prompt", choices=sorted(PROMPTS), default="v1",
                        help="which prompt version to use")
    parser.add_argument("--ocr-dir", default="cache/ocr",
                        help="folder with the OCR pieces the LLM reads")
    args = parser.parse_args()
    if args.ocr_dir != "cache/ocr" and args.name == "llm_groq":
        sys.exit("a different OCR folder must not write into the frozen llm_groq folder: "
                 "use --name llm_groq_paddle")
    ocr_dir = Path(args.ocr_dir)
    if args.prompt == "v2" and args.name == "llm_groq":
        sys.exit("v2 must not write into the frozen v1 folder: use --name llm_groq_v2")
    SYSTEM_PROMPT = PROMPTS[args.prompt]
    PROMPT_HASH = prompt_hash(SYSTEM_PROMPT)
    split = args.split
    is_test = split == "test"
    quiet = split != "validation"  # test and train print counts only, no receipt numbers
    if split == "train" and (args.limit is None or args.only):
        sys.exit("train needs --limit and does not allow --only")

    if is_test:
        from datasets import load_dataset
        check_test_set(load_dataset("naver-clova-ix/cord-v2", split="test"))
        if args.only:
            sys.exit("--only is for validation receipts only")

    raw_dir = Path(f"cache/{args.name}_raw")
    out_dir = Path(f"cache/{args.name}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    ids = args.only if args.only else list(range(args.limit or N_RECEIPTS))

    client = None
    if not args.reparse:
        load_dotenv()
        client = Groq()   # reads GROQ_API_KEY from the environment
    pacer = Pacer()
    stats = {"called": 0, "reused": 0, "failed": 0, "parse_error": 0, "cut_off": 0,
             "tokens": 0, "max_tokens": 0, "seconds": 0.0}

    try:
        for n, i in enumerate(ids, 1):
            raw_path = raw_dir / f"{split}_{i:03d}.json"
            record = json.loads((ocr_dir / f"{split}_{i:03d}.json").read_text(encoding="utf-8"))
            text = render_receipt(record["pieces"], CURRENCY)

            raw = None
            if raw_path.exists():
                saved = json.loads(raw_path.read_text(encoding="utf-8"))
                if args.reparse or saved.get("prompt_hash") == PROMPT_HASH:
                    raw = saved
                    stats["reused"] += 1
            if raw is None:
                if args.reparse:
                    continue
                estimate = (len(SYSTEM_PROMPT) + len(text)) // 3 + 1200
                pacer.wait(estimate)
                error_text = None
                try:
                    reply, finish, usage, seconds = call_groq(client, text)
                except BadRequestError as err:
                    # The model's JSON did not fit the schema. That is a real outcome of
                    # this arm, not a network problem: save it as "no answer", keep the evidence.
                    print("  one schema failure, saved as no answer" if quiet
                          else f"  val {i:03d}: schema failure, saved as no answer")
                    reply, finish, seconds = None, "schema_error", 0.0
                    usage = {"prompt": 0, "completion": 0, "total": 0, "reasoning": None}
                    error_text = str(err)
                except APIError as err:
                    stats["failed"] += 1
                    print(f"  call failed ({type(err).__name__}): {err}")
                    continue
                pacer.record(usage["total"])
                raw = {"index": i, "split": split, "model": MODEL,
                       "prompt_hash": PROMPT_HASH, "text": text, "reply": reply,
                       "finish_reason": finish, "usage": usage, "seconds": seconds,
                       "error": error_text}
                # saved BEFORE parsing
                raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
                stats["called"] += 1
                stats["tokens"] += usage["total"]
                stats["max_tokens"] = max(stats["max_tokens"], usage["total"])
                stats["seconds"] += seconds

            answer = parse_reply(raw["reply"])
            result = answer_to_result(answer, CURRENCY, i)
            (out_dir / f"{split}_{i:03d}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
            stats["parse_error"] += answer is None
            stats["cut_off"] += raw["finish_reason"] == "length"

            if not quiet:
                if args.only:
                    show_trial(i, raw["text"], raw, result)
                else:
                    u = raw["usage"]
                    print(f"val {i:03d}: {u['total']} tokens (reasoning {u['reasoning']}) "
                          f"{raw['seconds']:.1f} s")
            elif n % 10 == 0:
                print(f"  {n} of {len(ids)} done")
    except DailyLimit as err:
        print(f"\nSTOPPED: {err}. Everything finished so far is saved; run the same "
              f"command later and it resumes.")

    print(f"\nprompt version {PROMPT_HASH}, model {MODEL}")
    print(f"  called Groq: {stats['called']}   reused from disk: {stats['reused']}   "
          f"failed: {stats['failed']}")
    if stats["called"]:
        print(f"  tokens this run: {stats['tokens']}  "
              f"(average {stats['tokens'] // stats['called']} per call, "
              f"largest {stats['max_tokens']})")
        print(f"  average time: {stats['seconds'] / stats['called']:.1f} s per call "
              f"(sleeping for pacing not included)")
    print(f"  replies with no usable answer (invalid JSON or schema failure): {stats['parse_error']}")
    print(f"  replies cut off at the token cap: {stats['cut_off']}")


if __name__ == "__main__":
    main()