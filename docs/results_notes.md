Day 2. Raw total-visible rate (EasyOCR, whole piece or any word, no merging): test 53/95 = 55.8% (strict rate identical), validation 61/98 = 62.2%. Median 9.1 s/image on test. Pre-committed rule: if the MERGED rate (measured end of Day 3) is below ~80%, try a second engine on the same cache; otherwise keep EasyOCR.

Day 3. MERGED total-visible rate (row tol 0.5, JOIN_GAP 1.0, repair A: zero-like letters + separator + stray quote; IDR): validation k/98 = x% (optimistic: rules tuned on validation); TEST k/95 = x% (stop-rule number). Rule: test < ~80% -> try a second engine on the same cache.

Day 3. DEVIATION from the pre-committed rule: merged TEST rate 72/95 = 75.8% < ~80%, so the rule said to try a second engine. Decided NOT to: the shortfall is 4 receipts (within sampling noise at n=95) and the trial costs about half a day for an uncertain gain. Consequence: EasyOCR stays unbenchmarked against alternatives (README limitation). Remaining errors (digit misreads, garbage OCR) are exactly what the validator is for.

Day 4: Scorer frozen (src/score.py; items matched by price only, review = no answer). Cross-check passed: scorer total correct 57/98 = quick check 57/98. Extractor v1 on validation: total precision 79.2%, recall 58.2%; items precision 61.7%, recall 63.9%; receipt exact match 17/100. Count agreement 14.1% mixes "not extracted" with "wrong".

Day 4: Extractor v1 on TEST (scored once): total precision 78.5%, recall 53.7% (51 correct, 14 wrong, 30 no answer, of 95 scored); subtotal 97.1% / 53.1%; tax 68.2% / 37.5%; service 80.0% / 66.7% (only 12 receipts). Items precision 59.9%, recall 61.2%. Receipt exact match 18/100. Validation total recall was 58.2%: a 4.5-point gap, about one standard error at n=95, so not treated as a real difference. Readable ceiling on test 72/95 vs returned 51/95: 21 receipts where the answer is on the page and v1 misses it. This is the v1 "before". Scorer and v1 are frozen.

Day 4, v2 fix 7 (fuzzy total/subtotal keyword, one edit allowed, 4+ letters, runs only on lines v1 left unclassified), VALIDATION: total correct 57 -> 66, wrong 15 -> 16, no answer 26 -> 16 (precision 79.2% -> 80.5%, recall 58.2% -> 67.3%). 9 of 9 targeted receipts fixed, 0 regressions, 1 new wrong (val 2: a "Tota]" line that is probably the cash row). Subtotal correct 33 -> 36 but wrong 4 -> 6 (val 2, val 71: silent zero). Items precision 61.7% -> 66.0% (15 fake items gone), exact match 17 -> 21. Not done under rule A2 (helps under 3 receipts): neighbouring row (2 receipts), "Total Qty" exclusion spelling (2), payment-row cases (would break decision 2A).

Day 4, v2 zero diagnosis (validation): 11 zero-price items in 9 receipts; the label itself has price-0 items in 6 receipts (plastic bags, cup lid), so 0 is a review signal, not an error. Stray-0 fix reaches 1 receipt (val 47), modifier fix 1 (val 99): both skipped under rule A2. Zero-flagging and the 5 repaired all-letter zeros (digits lost) go to the Day 7 validator. Val 47 is the confident-and-wrong story (conf 1.00); val 99's fake modifier items add 0 to the item sum, so the arithmetic check cannot see them.
Day 4, v2 on TEST (scored once, after all validation work): total precision 79.4%, recall 56.8% (54 correct, 14 wrong, 27 no answer, of 95); subtotal 95.0% / 59.4%; tax and service unchanged (68.2% / 37.5%, 80.0% / 66.7%). Items precision 62.8%, recall 60.7%. Exact match 18 -> 21. Total recall gain: +3.1 points on test vs +9.1 on validation (validation optimistic, rule built from its misspellings). Costs: subtotal wrong 1 -> 2, items matched 148 -> 147, both unexplained (no test indices browsed).
Day 4 CLOSED: scorer and extractor v2 frozen. Not done under rule A2 or moved: neighbouring row (2 receipts), exclusion-word spelling Aty/itea/@ty (2), payment-row total (would break decision 2A), zero items (1 each), discount sign, x1 count. Day 7: zero flags, tiny totals, cash/change extraction.

## Day 5: LLM arm (Arm 2), prompt v1 frozen

Design: merged + repaired lines (same text as the rules arm), no OCR confidence shown to the LLM, strict JSON schema with null allowed, amounts copied as printed and converted by parse_amount, evidence line required for each summary field, total only from a TOTAL line (no fallback to the largest number). Model openai/gpt-oss-120b via Groq, temperature 0, reasoning_effort low. Only OCR text leaves the machine.

Tokens: about 1,300 per call (validation 100 receipts about 128K tokens). One of the first 100 validation attempts failed schema validation (400: model returned menu as an object); the retry passed, so the failure is not deterministic at temperature 0. Connection errors on receipts 70-99 were network failures, resumed from the cache.

Validation (v1): total 65/13/20 (prec 83.3%, recall 66.3%), subtotal 40/8/19, tax 27/6/14, service 7/3/3, items matched 150, exact 24/100. Rules v2 on validation: total 66/16/16.
Overlap of the two arms on total (validation): 61 both right, 10 both wrong, 14 both no answer; LLM right and rules wrong 2 (+2 on rules no answer), rules right and LLM wrong 3 (+2 on LLM no answer).
Val 94 was a false hit in v1 (evidence line was an e-gift payment row, number equalled the label).

Prompt v2 (rule 5a, pre-committed: keep only if validation total correct >= 68): rule 2 extended to GRAND TOTAL, lowest total line, rightmost amount. Result 67 correct (+4 fixed: 4, 63, 74, 86; -2 broken: 70, 94). NOT adopted; v1 is final. Subtotal and tax moved by 1-2 receipts under a change that does not touch them, so a +2 is inside run-to-run noise. Files kept in cache/llm_groq_v2.

Test (v1, run once, counts only): total 54/11/30 (prec 83.1%, recall 56.8%, 1 extra), subtotal 39/2/23, tax 17/6/17, service 9/3/0, items matched 151 of 242 label items, exact 23/100. Rules v2 on test: total 54/14/27, exact 21/100. Both arms stay 18 receipts below the readable ceiling (72).
Day 7 notes: only 11 (LLM) and 14 (rules) wrong totals on test, so report counts, not only percentages. Add a check that the evidence line contains a total word (catches false hits like val 94).
Day 5 CLOSED.
## Day 6 (Oct 22-24): PaddleOCR as a second OCR engine

**Reversal of the Day 3 decision (written down).** Day 3 decided not to try a second OCR engine. Reversed because Day 5 showed both extractors stop about 18 receipts below the readable ceiling, so the OCR text is the limit. Engine: PaddleOCR, chosen by me after checking its current state. Pre-committed before any number: 90-minute install cap; run on test regardless of the validation result (2a); Paddle becomes the main OCR if validation merged+repaired readable is at least 87 of 98 (EasyOCR: 84). Result: 96 of 98, so Paddle is the main OCR.

**Setup.** Separate venv .venv-paddle (Python 3.12.7) so the frozen EasyOCR pipeline is untouched. paddlepaddle 3.2.2 pinned (3.3.0 had a reported CPU regression). setuptools had to be installed by hand (Paddle imports it but does not declare it). Models: PP-OCRv6 medium detector and recognizer, English. The three optional steps (page orientation, unwarping, text-line orientation) are OFF; not tested ON. Detector long side capped at 2560 (the default of 4000 crashed on validation receipt 3, 2304x4096). Cache: cache/ocr_paddle (100 validation + 100 test). Merge, repair and extractor constants were NOT retuned. Median seconds per image: validation 5.9, test 6.4 (EasyOCR about 9 from earlier notes; different runs, not a controlled comparison).

**Readable = the correct total appears as a parseable number in the text. NOT accuracy.**

| | EasyOCR raw | EasyOCR merged+repaired | Paddle raw | Paddle merged+repaired |
|---|---|---|---|---|
| validation (98) | 62.2% | 84 = 85.7% | 95 = 96.9% | 96 = 98.0% |
| test (95) | 55.8% | 72 = 75.8% | 94 = 98.9% | 94 = 98.9% |

Repair is almost idle on Paddle text (validation: 1 separator fix; test: 1 zero-like-letter fix). On EasyOCR validation it made 125 letter-to-zero fixes.

**Rules arm v2 (frozen), correct / wrong / no answer.**

| | val EasyOCR | val Paddle | test EasyOCR | test Paddle |
|---|---|---|---|---|
| total | 66/16/16 | 86/5/7 | 54/14/27 | 73/5/17 |
| subtotal | 36/6/25 | 52/1/14 | 38/2/24 | 48/0/16 |
| tax | 24/7/16 | 39/2/6 | 15/7/18 | 31/1/8 |
| service | 4/1/8 | 7/1/5 | 8/2/2 | 9/1/2 |
| items matched | 140 of 219 | 182 of 219 | 147 of 242 | 211 of 242 |
| exact match (of 100) | 21 | 43 | 21 | 39 |

Test Paddle total: precision 93.6%, recall 76.8%. Test Paddle items: returned 286, precision 73.8%, recall 87.2% (precision is lower than recall because the arm returns more items than the label has; 6 item prices unreadable).

**Readings.** (1) The OCR was the bottleneck: swapping it gained 19 test totals (54 to 73); swapping the extractor never gained more than 1. (2) The bottleneck moved: the correct total is readable on 94 test receipts but returned correctly on 73, so about 21 receipts of pure extraction work (counts agreement, not a receipt-by-receipt match). (3) Validation is optimistic for the extractor, not for the OCR: readable 98.0% vs 98.9%, but total recall 87.8% (val) vs 76.8% (test). (4) Only 5 wrong totals on test: the validator's error pool is small; report counts and pool fields.

**Crash notes (cause NOT identified).** Paddle's native code is intermittently unstable on this machine.
- Validation receipt 3 (2304x4096): "RuntimeError: Unknown exception" at the detector with the default 4000 cap; passed with the 2560 cap in the full run.
- Test: one "Unknown exception" at 2560, then two runs ended silently (10 and 20 receipts, no traceback). The crash printer was not on then. A later probe showed a Windows access violation (native crash, no Python traceback) at size 4000, so the silent stops are consistent with that but not proven.
- Probe on validation receipt 3, one process, ascending sizes: 960-2048 ok, 2560 failed, 3000 failed, 4000 crashed hard. My probe was badly designed (size and number of earlier calls moved together).
- Four fresh-process reruns could not reproduce it: 2560 ok twice, 2048 then 2560 ok. With oneDNN off, 2048/2560/3000/4000 all ok but 7 to 9 times slower (2048: 9.2 s vs 64.9 s), so not adopted.
- Machine: about 6 GB RAM, about 0.85 GB free at one check. Peak memory 1.2 GB (2048), 1.5-1.6 GB (2560), 3.5 GB (4000, oneDNN off). Memory pressure is a plausible lead, not shown.
- Test files: 98 at detector size 2560, 1 at 1600, 1 at 1280 (the two fell back after errors). Indices not looked up (test rule). A crash never writes a file; integrity check: 200 files, 0 empty, indices match, no leftover .tmp files.
- Policy: existing caches are not rerun; Paddle runs through the restart-and-resume loop; own receipts and the demo run Paddle in its own process with a detector cap of 2048 or lower; crash log goes to cache/paddle_crash.log.

**For the README.** (1) Second engine tried and adopted; reversal of the Day 3 decision with these numbers. (2) Paddle crashed intermittently on large images; cause not identified; 2 of 100 test receipts were read at reduced detector size. (3) Merge and repair constants were tuned on EasyOCR output and not retuned. (4) PP-OCRv6, English, three optional steps off. (5) Not tested: the three optional steps ON, French or Arabic models, Tunisian receipts.

## Day 6 addendum (Oct 24): frozen LLM arm on Paddle text

Prompt v1 (hash 4aa66db7), gpt-oss-120b, unchanged. Folder cache/llm_groq_paddle (+ _raw); the frozen EasyOCR-text folder cache/llm_groq is untouched. Reuse guard added to run_llm.py: a saved reply is reused only if the prompt hash AND the input text match. Check: the stored LLM input differs from Paddle's text on 0 of 100 receipts, validation and test (5 test replies were reused from an earlier start; they were fine).

Tokens: validation 124,606 (average 1,246 per call, largest 1,997); test 121,347 for 95 calls (average 1,277, largest 1,884). 0 schema failures and 0 cut-offs in both splits. The two runs used about 246K tokens in one afternoon without stopping at the free daily cap shown in the console (200K), so how the cap is counted is NOT understood.

Correct / wrong / no answer, both arms reading Paddle text:

| | val rules | val LLM | test rules | test LLM |
|---|---|---|---|---|
| total | 86/5/7 | 85/6/7 | 73/5/17 | 73/0/22 |
| subtotal | 52/1/14 | 53/1/13 | 48/0/16 | 50/1/13 |
| tax | 39/2/6 | 39/2/6 | 31/1/8 | 33/1/6 |
| service | 7/1/5 | 11/1/1 | 9/1/2 | 11/1/0 |
| items matched | 182/219 | 202/219 | 211/242 | 220/242 |
| exact match (of 100) | 43 | 50 | 39 | 46 |

LLM items: validation returned 222 with 45 unreadable prices; test returned 255 with 17 unreadable. Count agreement 73.9% (val) and 69.2% (test) vs 22% for the rules; partly structural, not an accuracy gap.

Readings. (1) Total recall ties again: 73 = 73 on test; the correct total is readable on 94, so about 21 receipts are not returned by either arm. (2) The LLM was never wrong on a test total but left 5 more unanswered; 0 wrong of 73 answered still allows a true wrong rate of about 4%. (3) The LLM leads on items and exact match (+7 on both splits), small on single fields.

Nine validation failures read (text only, nothing built). Amount alone on the line above a keyword-only line: 41, 92, 94, 97 (94: the LLM took the e-gift payment row instead, evidence line without a total word). Rows shifted by one: 16, 38, 23. Keyword fused into the cash line: 47. Amount refused (leading dot ".26.000"): 68, correctly sent to review. Validation 66 and 73: total not readable in the text.

## Day 6 addendum 2 (Oct 24): rules v3, a keyword-only total line takes the amount-only neighbour

Pattern seen on 4 of 9 validation failures read by eye (text only): the amount sits alone on the line above a keyword-only TOTAL line (vals 41, 92, 94, 97). Rule: only when v2 found NO total, and a total-keyword line has no amount, use the line directly above if it is exactly one amount with no words; mode "both" also looks below; if both neighbours qualify the result is "review" with no value (decision 3b). Decisions 1GO 2b 3b were mine. Stop rule written before any number: keep v3 only if validation total correct is at least 89 of 98 (v2: 86), cap 1 hour (used about 10 minutes). Rules v2 stays frozen; default is adjacent=off.

Safety: with the switch off, 100 validation files were byte-identical to the frozen v2 files. Tests: 94 pass (85 + 9 new).

Validation total (correct/wrong/no answer): v2 86/5/7 -> v3 above 90/5/3 and v3 both 90/5/3 (identical). Exact match 43 -> 44. Wrong list unchanged (16, 23, 38, 47, 61). Fixed: 41, 92, 94, 97. Left: 66, 73 (total not readable), 68 (leading dot refused, flagged for review).
Test total: v2 73/5/17 -> v3 both 74/5/16; every other field and exact match (39) unchanged. How the total was found: validation 93 normal rule, 4 above, 0 below, 0 ambiguous, 3 none; test 80 normal, 1 above, 0 below, 0 ambiguous, 19 none.

Readings. (1) The rule was written from the four validation receipts it fixes, so 4 of 4 is built in; on test it fired once (and was right): validation is optimistic, as with the Day 4 fuzzy fix (+9 val, +3 test). (2) The "below" lookup and the "ambiguous -> review" branch never fired on real data; they exist only in unit tests. (3) Wrong totals are untouched by v3: the wrong-row receipts (16, 38, 23, 47) have an amount on the TOTAL line, so the rule does not run; they are for the validator. (4) Remaining gap on test: correct total readable on 94, returned correctly on 74.

## Day 7 (Oct 25): generic validator, FROZEN before the test run
What it is: src/validate.py takes one extraction record (and the OCR text for the LLM arm) and returns flags, each with a code and a plain reason. It never sees the image. A check that cannot run (no items, no subtotal) is "not evaluable", never a pass.

Decisions (all written before any test number):
- 1c tolerance = 1 rupiah, chosen from a validation table. From 1 to 1000 the result moves by at most one error record and one false alarm; only 0 -> 1 matters (it spares 3 rounding cases like val 2). The dinar tolerance is a Day 8 question.
- 2a/6b: every flag carries a reason. The REVIEW QUEUE (decision 6b) = value-based flags (TOTAL_VS_BASE, ITEMS_VS_SUBTOTAL, CASH_CHANGE_TOTAL, TINY_TOTAL, NUMBER_NOT_IN_TEXT, EVIDENCE_NOT_IN_TEXT, TOTAL_WORD_MISSING) plus MISSING_TOTAL and FIELD_REVIEW. NO_ITEMS, ZERO_PRICE, ITEM_UNREADABLE and REPAIRED stay on the record as notes but do not queue a receipt. REASON FOR THE CHANGE: with any-flag the review rate on Paddle text was 45-50 of 100, which I judged not useful. This was changed in writing after seeing validation numbers, so validation is optimistic.
- 3c cash/change finder (same-line only), scored against CORD cashprice/changeprice on validation. Paddle text: cash 47 correct, 3 wrong, 14 not found (of 64); change 50 correct, 0 wrong, 13 not found (of 63). EasyOCR text much weaker (cash 27/10/27). It works as a confirmation (cash - change = total on 32 of the 33 receipts it could run on, rules/Paddle), not as a catcher.
- CASH_SHORT (cash < total) was DROPPED by the 3-receipt rule: sole catch on 1 receipt, 3 false alarms per Paddle pipeline.
- 4a grounding on the LLM arm: EVIDENCE_NOT_IN_TEXT fired on 0 records; TOTAL_WORD_MISSING is the check that does work (val 94).
- 5a headline = records with a WRONG value in total/subtotal/tax/service; missing fields reported separately; false alarms and review rate always next to it. Items are not part of the error group, so some false alarms may be real item errors (not measured).

Validation, queue, tolerance 1 (error records in queue / clean records in queue / review rate):
rules Paddle 6 of 7 / 6 of 71 / 30 of 100; LLM Paddle 7 of 8 / 7 of 70 / 27 of 100; rules EasyOCR 21 of 22 / 12 of 44 / 63; LLM EasyOCR 21 of 23 / 18 of 48 / 63.
Strict variant (any flag) on Paddle: 7 of 7 and 7 of 8 caught, review rate 50 and 45.
Misses: val 23 (rules, Paddle; only NO_ITEMS flagged it), val 63 (LLM, Paddle; every gap 0, not yet investigated).

STOP RULE: Decision 6 was the last change to the alarm. The test is run ONCE, counts only; nothing is changed afterwards; whatever it shows goes in the README. Expected test error pools are tiny on Paddle (rules about 6-7 records with a wrong field, LLM about 3), so report counts.

## Day 7 test result (Oct 25): generic validator, run ONCE after the freeze (commit 8d8f52c)
Tolerance 1, queue = decision 6b. Sanity: all four total counts matched the frozen test scores. Counts only.

Error records in queue / clean records in queue / missing-field receipts in queue / review rate:
rules Paddle 6 of 6 / 19 of 66 / 27 of 28 / 52 of 100
LLM Paddle 2 of 2 / 18 of 69 / 26 of 29 / 46 of 100
rules EasyOCR 22 of 22 / 16 of 40 / 36 of 38 / 74 of 100
LLM EasyOCR 16 of 19 / 13 of 42 / 36 of 39 / 65 of 100
Strict any-flag review rate: 65 (rules Paddle), 59 (LLM Paddle), 86 and 76 (EasyOCR).
Pooled queue: 46 of 49 error pairs, 26 distinct receipts, 23 queued in every pipeline where they are errors.

Validation vs test (Paddle): review rate 30 -> 52 (rules), 27 -> 46 (LLM); clean records queued 6 of 71 -> 19 of 66 and 7 of 70 -> 18 of 69. Validation was optimistic as warned. By my own bar (half is barely acceptable) rules Paddle narrowly misses, LLM Paddle narrowly passes.
Composition of the queue, rules Paddle: 6 wrong + 27 missing-field + 19 clean. The 27 are receipts the extractor already could not answer. The validator's own cost is the 19.
Passed-through pile: rules Paddle 48 receipts with 0 wrong-value records; LLM Paddle 54 with 0. Error pools are 6 and 2, so 0 misses still allows a true miss rate near 40%. Items are not in the error definition.
Free catches: both LLM Paddle error records were queued by MISSING_TOTAL; only 1 of 2 by a value check. Rules Paddle: 5 of 6 by a value check (TOTAL_VS_BASE 5, TINY_TOTAL 4).
Likely causes of the extra false alarms (NOT verified): 4 clean records per Paddle pipeline carry MISSING_TOTAL (inference: their labels have no total); ITEMS_VS_SUBTOTAL on 9 clean records (rules Paddle) vs 4 on validation, consistent with item precision 73.8% on test, but not checked.
Plan: no change to the alarm. Day 8: break down false alarms by cause (validation first, test counts only, marked post-hoc); evaluate on own Tunisian receipts (unseen).
