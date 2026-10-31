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

## Day 7 addendum (Oct 25): review-queue breakdown, VALIDATION only. Decision 8c: no further change to the alarm.
Script: scripts/queue_breakdown.py (measurement only, changes no check). Test not broken down (would be tuning on test).

rules Paddle, validation, 30 receipts in the queue: 6 wrong-value records (true catches); 3 total not found; 2 label has no total (val 29, 49); 13 total CORRECT but subtotal/tax/service empty and arithmetic fired; 5 clean but items differ from the label; 1 clean unexplained (val 33, cash/change).
LLM Paddle, validation, 27 in the queue: 7 wrong-value; 7 total not found; 1 + 1 label has no total (val 29 and val 49); 5 total correct but another field empty; 3 clean with items differing (val 7, 61, 76); 3 clean unexplained (val 8, 33, 55).
Test (from the flag table, NOT a measured breakdown): rules Paddle queued 27 of 28 missing-field receipts but only 15 carry MISSING_TOTAL, so about 12 are probably the same kind (inference).

FINDINGS
1. Correction to my earlier claim that the missing-field receipts "need a human anyway": on validation rules/Paddle only 3 of 18 are "no total found". Thirteen have a correct total; the arithmetic check fires because an absent tax or service is treated as 0.
2. The validator cannot tell "tax missing, total right" from "total wrong": both break the sum the same way. Relaxing the first could hide real errors (val 61, off by 5,700).
3. Of the 6 rules/Paddle false alarms, 5 have item prices that differ from the label (my error definition ignores items, so some may be real catches). Val 7 is a known genuine false alarm (discount line). Lower bound about 1 true false alarm, upper bound about 6.
4. Label without a total (val 29, 49) counts as clean but is queued by MISSING_TOTAL: a definition artifact, not noise.
5. Rough estimate (NOT a result): a perfect fix for finding 1 would take rules/Paddle from 30 to about 20 on validation; a realistic test gain is smaller. Not built.

FUTURE WORK (untested): treat an absent tax/service as unknown instead of 0, with a gap-size rule written before test; score items in the error definition.

## Day 7 addendum (Oct 25): false-alarm breakdown, 8b rejected, Tunisian part dropped
Breakdown of the review queue on validation (scripts/queue_breakdown.py; test counts only if ever run, post-hoc):
- rules Paddle, 30 in queue: 6 wrong-value records, 3 extractor found no total, 2 label has no total (val 29, 49), 13 total right but subtotal/tax/service empty and arithmetic fired, 5 clean with items differing from the label (val 7 is the discount case), 1 unexplained (val 33, cash/change).
- LLM Paddle, 27 in queue: 7 / 7 / 1 label without total (val 49) / 5 / 3 / 3.
- CORRECTION: I called the 13 a "missing-tax artifact". Checked against label amounts it holds for 3 of 13 (val 45, 48, 25); 6 have no subtotal (base is a partial item sum, gaps up to 50%); 4 match nothing.
8b (written first): adopt a gap-band rule only if, on validation across all four pipelines, 0 wrong-value records leave the queue and at least 3 receipts leave. Result at 3-12%: rules Paddle 4 leave / 0 lost; LLM Paddle 0 / 0; rules EasyOCR 1 / 2 lost; LLM EasyOCR 1 / 1 lost. REJECTED. A missing tax (~10% of base) and a total wrong by ~10% look identical to the validator. Paddle-only would have passed; not used, because the rule said four pipelines. No check changed. Frozen test numbers stay the headline (rules Paddle 52, LLM Paddle 46 of 100).
What would lower the rate: extractor fixes for empty subtotal/tax/service (closed under the Day 6 stop rule), not validator rules.
PLAN CHANGE: Tunisian rules and own-receipts evaluation DROPPED. Reason: no Tunisian receipts available, so no rule could be tested, and the VAT/matricule facts came from secondary sources. README keeps one limitation line (dinar amounts are unit-tested in the normalizer; no Tunisian receipts evaluated; CORD is Indonesian). CV line loses the Tunisia clause.

## Train-split confirmation run: FROZEN PLAN (written before any train number exists)
Why: test error pools are tiny (rules Paddle 6 wrong-value records, LLM Paddle 2). Train was never used for tuning, so it is a second clean holdout for the FROZEN validator (tolerance 1, queue 6b). No check changes.
- Receipts: train indices 0-399 in dataset order. None picked or skipped.
- OCR: Paddle only, same settings, same restart-and-resume loop. EasyOCR is not run on train.
- Extractors: rules v3 "both" on all 400. LLM arm (frozen prompt v1) on indices 0-99 only (about 125K tokens, under the daily cap).
- Validator runs (both fixed now): (1) rules Paddle on 0-399; (2) rules Paddle and LLM Paddle on 0-99, so the two arms are compared on the same receipts.
- Reporting: counts only, no receipt indices; train is not browsed to tune anything. No expected-count match line (train has no frozen scores); the scorer's correct/wrong/no-answer counts are read against test as a plausibility check.
- Stop rule: the numbers that print go in the README, even if worse than test. Nothing is changed afterwards.

## Day 7 addendum 2: train-split confirmation (plan frozen before any train number; commit of the plan: see notes above)
Train indices 0-399, Paddle OCR only. OCR integrity: 400 files, 0 empty, 0 mismatches; detector size 393 at 2560, 6 at 1600, 1 at 1280 (7 of 400 reduced); median 17 pieces per receipt. Rules v3 "both" on all 400; LLM prompt v1 (hash 4aa66db7) on 0-99 (127,650 tokens, 0 schema failures, 0 cut-offs). Validator frozen (tolerance 1, queue 6b), counts only.

Rules + Paddle, train 400: total 324 correct / 10 wrong / 57 no answer (recall 82.9% of 391 scored; validation 91.8%, test 77.9%). Queue: wrong-value records 23 of 24, clean receipts 50 of 256, missing-field receipts 93 of 120, review rate 166 of 400. Strict any-flag review rate 256 of 400; value-based only 115 of 400.
Rules vs LLM on train 0-99: rules caught 3 of 4, 12 of 59 clean queued, review 46; LLM caught 5 of 8, 10 of 60 clean queued, review 40. LLM total 69 / 6 / 23 vs rules 76 / 2 / 20.
Pooled unseen splits (test + train), rules Paddle: 29 of 30 wrong-value records queued; 69 of 322 clean receipts queued; review rate 218 of 500.
READINGS: (1) catch held up on a 4x larger pool; (2) review rate 30 (val), 52 (test), 41.5 (train): validation was optimistic; (3) NOT achieved: 20-25% review rate; the rest of the queue is extractor gaps (54 of 93 missing-field receipts have no total) plus 50 false alarms, whose item-error share is unmeasured; (4) "LLM never wrong on a test total" does NOT replicate (test 0 of 73; train 6 of 75; validation 6 of 91): test was the lucky split; (5) on the LLM's 8 wrong-value records TOTAL_VS_BASE caught 0, cash/change 3, MISSING_TOTAL 2; grounding checks caught 0 of 8 on train and 0 of 2 on test (1 on validation, val 94): grounding rarely fires on errors.
Limits: train pools are 24 (rules) and 4/8 (first 100); train was only counted, never browsed; the run header "four pipelines" is a stale label in run_validate.py.

## Day 8 - Decisions 10 and 11: error-analysis sample (written BEFORE any holdout B receipt is browsed)

NAMING (README, notes, demo): "holdout B" = the first 400 receipts of CORD's train split (indices 0-399). Nothing in this project is trained and nothing was tuned on it. "Development set" = CORD validation (100 receipts; used for all design and tuning). "Test" = CORD test (100 receipts; frozen verdict; counts only, never browsed). The README says once that holdout B is CORD's train split.

DECISION 10 (where the failures come from): holdout B, not validation (validation was developed on and is used up for this) and not test (test stays counts-only, never browsed). Holdout B was counted first (Day 7, addendum 2, line 177) and is browsed afterwards for error analysis ONLY. Nothing in the extractor, merge, repair or validator changes afterwards. The ~20 browsed receipts are no longer unseen; the other ~380 are untouched. The 400-receipt counts were taken before any browsing and stay valid. Git order caveat: one end-of-day commit, so the order "plan, then browsing" is shown only by the order of notes lines, not by separate commits.

DECISION 11c (sample design): 20 receipts = 8 wrong-value + 6 no-total + 6 false alarm. All rules v3 "both" on Paddle text, validator frozen (tolerance 1, queue 6b). Nothing is recomputed with other settings.

POOLS (defined by the existing scorer and validator):
- Wrong-value: the "error" group (a wrong value in total, subtotal, tax or service). Expected size 24 (23 queued, 1 missed by the validator).
- No-total: record total is empty AND the label has a total. Expected size before precedence: 57 (the Day 7 total no_answer count on holdout B). Precedence: a receipt in the wrong-value pool is removed from this pool.
- False alarm: the "ok" group (every labelled field correct) that the validator queued. Expected size 50.

DRAW (fixed now, run once, no redraw): seed 42. One random.Random(42) instance. Index lists sorted ascending. Order of draws: (1) wrong-value: the one missed receipt is always included, plus 7 sampled from the 23 caught; (2) no-total: 6 sampled; (3) false alarm: 6 sampled. If the drawn 20 look unrepresentative or uncomfortable, no redraw.

SAFETY CHECK before printing anything: the script prints the pool sizes (counts only). If wrong-value is not 24, or false alarm is not 50, or wrong-value + no-total (before precedence) is not 57, it stops and prints nothing else (something drifted from Day 7).

AFTER THE DRAW: only the 20 drawn indices are ever printed. No other holdout B receipt is browsed. A real bug found is written down as "found, not fixed".

WHAT THE SAMPLE CAN AND CANNOT SAY: it is built by category (8/6/6), so it is NOT representative. It shows which KINDS of failure exist and which stage caused them, not how often each kind happens. The false-alarm cards are a first look at whether "false alarms" hide real item errors (items sit outside the error definition; unmeasured so far).

ADDENDUM (same day, before any draw): the safety check line above is worded wrongly. The correct check is: wrong-value pool = 24, false-alarm pool = 50, no-total pool BEFORE precedence = 57 (not "wrong-value + no-total = 57"). The no-total pool AFTER precedence may be smaller than 57. Nothing else changes.

## Day 8 - Decision 12a, 13a and the FROZEN category list (written BEFORE any case card is shown)

DRAW RESULT (holdout B, rules v3 "both" on Paddle text, validator frozen; seed 42; run once; saved in cache/scores/holdout_b_sample.json). Safety check: all seven pool lines MATCHED Day 7 (error 24, missing 120, ok 256, caught 23, missed 1, false alarm 50, total no_answer 57). No-total pool AFTER precedence = 53 (4 of the 57 also have a wrong subtotal/tax/service, so they sit in the wrong-value pool).
- wrong-value, missed by the validator: 88
- wrong-value, caught (7 sampled): 1, 116, 147, 197, 215, 351, 376
- no total (6): 27, 29, 202, 310, 381, 392
- false alarm (6): 3, 5, 52, 122, 210, 279

DECISION 12a: when a receipt has two causes, the EARLIEST stage wins (OCR/merge, then repair, then extractor, then normalizer). The second cause goes in the free-text note of the card.
DECISION 13a: a "label issue" category exists. It is used ONLY when the pipeline output matches what is printed on the paper and the label disagrees with the paper. If the pipeline is also wrong, the normal rule applies.

STAGE NOTE: OCR and merge are ONE stage in the tally ("OCR/merge"), because from the text alone a wrong row or a split number cannot be assigned to one of them.
CORRECTION: my first list had no repair category. Added before any card was shown; numbering below is the final one.

FROZEN CATEGORIES, part C (the 14 wrong-value and no-total receipts; exactly one primary category each):
- C1 OCR misread digit (recognition) - stage OCR/merge
- C2 OCR split a number or separator - stage OCR/merge
- C3 Row shift or wrong row association (val 16 type) - stage OCR/merge
- C4 Lost keyword (TOTAL misread or missing) - stage OCR/merge
- C5 Repair error (repair changed or refused a token wrongly) - stage repair
- C6 Total/subtotal confusion - stage extractor
- C7 Number-format error - stage normalizer
- C8 Modifier line or stray piece taken as an item or amount - stage extractor
- C9 Label issue - stage label
- C10 Other - stage unknown

FROZEN CATEGORIES, part V (the 6 false alarms; exactly one reason each). Precedence if more than one applies: V4, V2, V3, V1, V5, V6 (V4 first because it is the finding being looked for).
- V1 Total right, subtotal/tax/service empty, so the arithmetic fired
- V2 Discount line
- V3 Rounding
- V4 Real item error (items differ from the paper)
- V5 Label issue
- V6 Other or unexplained

RECEIPT 88 (the one wrong-value record the validator missed): gets a part C category PLUS a one-line miss note (check could not run / all gaps zero / other). No separate category.

WHAT THE TALLY CAN SAY: which kinds and which stages appear in 20 hand-picked failures (8/6/6 by design, not representative). It cannot say how often each kind happens. Categories are assigned by Claude from the text card and confirmed or overruled by the human looking at the image.

## Day 8 - Decision 14a and 15 (written BEFORE any case card is shown)

DECISION 14a: the fine categories (C1-C10, V1-V6) are used for ASSIGNING only. The HEADLINE of the error analysis is (a) a stage table over the 14 part-C receipts with coarse stages (OCR/merge, repair, extractor, normalizer, label, unknown) and (b) for the 6 false alarms: V4 (real item error) versus not V4. The fine list appears once, as "kinds seen", labelled "not a frequency table", counts only, no percentages. FREQUENCIES come from the counts on all 400 holdout B receipts (24 wrong-value / 120 missing-field / 256 clean; total 324/10/57; queue 23 of 24, 50 of 256, 166 of 400), NOT from the 20 cards. The cards say what kinds of failure exist and at which stage; the 400 counts say how often.

DECISION 15: run scripts/queue_breakdown.py on holdout B (rules_paddle, 400 receipts), counts only, post-hoc. It changes no check and prints no index. Code change: --split train (needs --limit) and a --pipes filter.

SANITY EXPECTATIONS (written before the run): receipts in the queue 166; clean records in the queue add up to 50; missing-field records in the queue add up to 93; "total itself unanswered" = 53.

CORRECTION: a figure "54 of the 93 queued missing-field receipts have no total" was used earlier (handover). It is wrong: the no-total pool outside the wrong-value pool is 53 and MISSING_TOTAL always queues. The breakdown prints the real number.

README RULE: the README gives "how often" from the 400-receipt counts and "what kinds" from the 20 cards. It says the 20 are drawn by category (8/6/6), are not representative, and that categories were proposed by Claude from the text card and confirmed or overruled by the human looking at the image.

## Day 8 - Decision 15 result: queue breakdown on holdout B (rules_paddle, 400 receipts, counts only, post-hoc)

SANITY (all matched the expectations written before the run): queue 166; clean in queue 4 + 37 + 9 = 50; missing-field in queue 53 + 38 + 2 = 93; "total itself unanswered" 53. (The earlier "54" was a miscount.)
Queue composition: 166 = 23 wrong-value caught + 93 missing-field + 50 clean.
CLEAN (the scorer's "ok" group) in the queue, by cause: label has no total 4; items differ from label (price multiset differs AND an arithmetic flag fired) 37; unexplained 9.
MISSING-FIELD in the queue, by cause: total itself unanswered 53; total right, other field empty, arithmetic fired 38; other 2. Empty fields among the 38: subtotal 20, tax 18, service 12 (a receipt can have more than one).

READING: the "false alarms" are false only with respect to the four headline fields. 37 of the 50 have items that differ from the label by price matching. This is NOT proven to be real item error (modifier lines, label sub-items and price-0 items can also make the lists differ). The pure upper bound for "alarm with no item difference found" is 13 of 256 clean receipts (4 label-has-no-total + 9 unexplained). Until the cards check it, the README says "false alarms by the headline-field definition (50 of 256); 37 of them differ from the label in their items; verified by eye on 6 receipts only".

PREDICTION (written BEFORE any card is shown): if the 37-of-50 share holds, about 4 of the 6 false-alarm cards should show an item difference (expected 4.4 by simple proportion; 6 cards cannot confirm a rate). A card counts as V4 ONLY if the image shows an item line on the paper that the record has wrong, missing or invented. A modifier line, a sub-item or a price-0 line that the label also leaves out does NOT count. Reading rule: V4 on 4 or more of 6 -> "most queued 'clean' receipts carry a genuine item error" (small-sample caveat); V4 on 1 or fewer of 6 -> "the item-difference test mostly picks up label/modifier artifacts".

## Day 8 - Batch 1 of the cards (cards 1-8: wrong-value pool), assigned from text, confirmed against the images
- Card 1, receipt 88 (validator MISSED): C6, extractor. Paper prints TOTAL on the pre-tax line; the real total is under Netto. Gap 0 through the tax-inclusive reading; cash/change could not run. Also a quantity misread (95 read as 96), harmless. FOUND, NOT FIXED.
- Card 2, receipt 1: C3, OCR/merge. Photo tilted; PB1 label grouped with the service amount, the tax amount alone on its row. Total missing because the paper says DUE (second cause, a keyword gap). Queued by MISSING_TOTAL only.
- Card 3, receipt 116: C1 (borderline; digits lost under a stamp, not read as other digits). Normalizer read "29,9" as 29.9 (second cause). Caught by TINY_TOTAL, ITEMS_VS_SUBTOTAL, TOTAL_VS_BASE.
- Card 4, receipt 147: C6, extractor. Two Subtotal lines (before and after a discount); the label keeps the first, the extractor took the second (which is consistent with the total). C9 does NOT apply (both numbers are on the paper). The validator rang because of the discount line (gap 2,727 = the discount), not because of a real error.
- Cards 5 and 6, receipts 197 and 215: C1 (borderline; a shadow hides the leading 7 of 74,000). SAME PAPER photographed twice, so the 7 caught cards are 6 distinct papers. Pooled counts treat them as two receipts; not checked for other duplicates in the 24.
- Card 7, receipt 351: C6 (weakest fit; a tax-base line "Dasar Pengenaan Pajak" taken as tax). The label stores the subtotal as a list, so the scorer skips it (unparseable label). Caught by TOTAL_VS_BASE because the wrong tax broke the tax-inclusive reading.
- Card 8, receipt 376: C1, OCR/merge (blurry photo; 8 read as 9 on three prices, 47,000 as 17,000, tax 16,480 as 16,180). Total missing because the paper says DUE (second cause). Caught by MISSING_TOTAL and ITEMS_VS_SUBTOTAL.
TALLY (8 cards, 7 distinct papers): OCR/merge 5, extractor 3. Validator on the 7 caught: 4 by a value check that sees the wrong number, 1 only by MISSING_TOTAL (card 2), 1 only through a discount line (card 4); cards 5 and 6 count once. Counts, not rates.

## Day 8 - Batch 3 (cards 15-20: false-alarm pool) and the final tally. Step 6 DONE: 20 of 20 cards, assigned from the text card and confirmed against the images.
- Card 15, receipt 3: V2. Discount line (19,000) printed before TOTAL; TOTAL_VS_BASE gap = the discount. Items and all fields right. Same mechanism as val 7 and card 4.
- Card 16, receipt 5: V4. Paper has 5 items; record has 4 (Lasagna and Spaghetti fused with price 0, Iced Cappuccino price 0, Gypsy Gelato 39 instead of 39,000; numbers split into pieces in the text; raw pieces not inspected). Gap 171,961.
- Card 17, receipt 52: V6. Paper has no total line (subtotal, cash, change only). Label has no total either, so V5 does NOT apply (label agrees with the paper). MISSING_TOTAL is true about the paper. The Day 7 breakdown name "label has no total" is misleading for this receipt.
- Card 18, receipt 122: V4 (invented item). Item "LEURNA pan 2000" built from the logo/header area; no such item on the paper. Gap 2,000 = the ghost item. Paper has no total line either. The cash finder returned 377, read from another receipt visible behind this one; no effect on the flags.
- Card 19, receipt 210: V4 (missing item). Blueberry Fuji 40,000 is absent from the record although the OCR text has the line; the reason was not looked into (item code not read). TOTAL_VS_BASE gap 40,000 = the lost item.
- Card 20, receipt 279: V4 (invented item). Header date line read as an item with price 9; gap 9 = the ghost item. The -7,000 void line is on the paper (the label omits it); not an error. Cash/change confirmed the total (55,000 - 40,000 = 15,000).
PREDICTION CHECK (written before any card): V4 on 4 or more of 6 -> reading 1. Result: 4 of 6. 95% interval for 4 of 6 is about 22-96% (Claude's calculation), so the README says "4 of 6 hand-checked", not "most".
CROSS-CHECK with the breakdown buckets (from reading the code): cards 16, 19, 20 are in the "items differ from label" bucket (37) and were real item errors by eye (3 of 3, n = 3). Card 18 is in the "label has no total" bucket because the code checks that first, so 37 is probably a LOWER bound for item differences. Cards 15 and 17 (no item problem) are in the remainder of 13 (9 + 4); 1 of the 3 cards from that remainder was an item error, so 13 of 256 is an UPPER bound for alarms with no item problem.
HEADLINE UNCHANGED: by the frozen definition (four fields) these 50 stay false alarms. The README reports that definition and, next to it, the hand-checked result.
FINAL TALLY part C (14 receipts, 13 distinct papers): wrong-value pool: OCR/merge 5 (C1 x4, C3 x1), extractor 3 (C6 x3). No-total pool: OCR/merge 1 (C3), extractor 5 (C4b x5). All: OCR/merge 6, extractor 8. Unused as a primary: C2, C4a, C5, C7, C8, C9, C10 (C2, C7, C8 appear as second causes). Part V: V4 x4, V2 x1, V6 x1.
PATTERN (counts, not rates; n = 8 and 6): wrong numbers came mostly from the OCR stage; missing totals mostly from the keyword rule (decision 2A).
FOUND, NOT FIXED (README "what I would do next"): (1) total-word list (TL, AMOUNT DUE, DUE, PAID); (2) no discount field (val 7, cards 4 and 15); (3) ghost items from logo/header/date lines (cards 18, 20; also TL/CG taken as items on card 9); (4) the scorer ignores wrong fields the label does not have (card 10: service "extra"); (5) cash finder can read a neighbouring receipt in the photo (card 18); (6) receipts with no total line on the paper are queued by MISSING_TOTAL (card 17); (7) Paddle's merge constants were tuned on EasyOCR (card 11).

## Day 8 - DEVIATION (written after cards 1-14 were seen) and Batch 2 (cards 9-14: no-total pool)
DEVIATION 1: the frozen C4 ("lost keyword", stage OCR/merge) mixed two failures. Split: C4a = OCR lost or misread the keyword (stage OCR/merge, unused so far); C4b = the paper uses a total word the extractor does not look for (stage extractor; OCR read it correctly). Reason: cards 9, 10, 12, 13, 14 print TL, AMOUNT DUE, TL, DUE, PAID. Filing them as OCR/merge would blame the wrong stage; C10 would hide a known stage. Cards 15-20 (part V) are not affected.
CLARIFICATION of 12a as applied from card 2 on: a card's category names the failure that put the receipt in its pool (wrong-value pool: the wrong field; no-total pool: why the total is missing). Other failures on the same receipt go in the note.
- Card 9, receipt 27: C4b, extractor. Paper prints TL (big type) for the total. Second cause: TL and CG lines taken as items (3 items vs 1 in the label). Queued by MISSING_TOTAL only.
- Card 10, receipt 29: C4b, extractor. Paper prints AMOUNT DUE. Second cause: TAKE AWAY CHARGE 1,000 (an item in the label) put into the service field; the scorer calls it "extra" (label has no service), so it is NOT counted as a wrong value. FOUND, NOT FIXED. Queued by MISSING_TOTAL and ITEMS_VS_SUBTOTAL (gap 1,000, a real record problem).
- Card 11, receipt 202: C3, OCR/merge. Big-print 51,000 sits between GRAND TOTAL and the BCA DEBI row and was grouped into the BCA row; GRAND TOTAL line has no amount; rules v3 does not fire (the BCA row has words). The number is on the page (readable) yet not returned. Merge constants were tuned on EasyOCR.
- Card 12, receipt 310: C4b, extractor (paper prints TL). Second causes: leading dot printed before every amount; OCR text has "TL.770.000" fused and ".770,000", which the normalizer refuses (item price unreadable, C7 note); a unit-price line "2X 385,000" taken as an item. Unknown whether TL would have worked if the dot had parsed.
- Card 13, receipt 381: C4b, extractor (paper prints DUE; the "total" inside SUBTOTAL does not count). Rest of the record correct.
- Card 14, receipt 392: C4b, extractor (paper prints PAID, no total word). Separate failure: subtotal amount sits on the row below "SUBTOTAL 4 PCS" (C3-type; v3 only fills totals); item names came out as the quantity lines 3X and 1X. Queued by MISSING_TOTAL and ZERO_PRICE.
TALLY cards 1-14 (13 distinct papers; cards 5 and 6 are one paper): OCR/merge 6 (C3 x2, C1 x4), extractor 8 (C6 x3, C4b x5). Counts, not rates.
FINDING (found, not fixed): 5 of the 6 no-total cards (drawn at random from 53) have a paper total word other than TOTAL (TL, AMOUNT DUE, DUE, PAID); cards 2 and 8 also had DUE as a second cause. n = 6, so the true share among the 53 could be about 36-100%. Decision 2A (total only from a "total" line, no fallback) costs this. Not fixed: Day 6 stop rule and today's no-change rule. The keyword list in extract_rules.py was not read.
VALIDATOR on the 6 no-total cards: all queued, all by MISSING_TOTAL (a free catch); card 10 also had a real item gap. No arithmetic check could run on cards 9, 12, 14.

## Day 8 - Step 8: speed / cost (OCR seconds read from the cache files; no new run; counts only)
OCR seconds per receipt (median / mean / p90 / max / total): Paddle validation 5.87 / 6.62 / 11.95 / 15.20 / 11.0 min; Paddle test 6.44 / 7.87 / 14.63 / 31.10 / 13.1 min; Paddle holdout B (400) 5.92 / 7.38 / 13.39 / 24.16 / 49.2 min; EasyOCR validation 9.58 / 13.36 / 36.66 / 48.30 / 22.3 min; EasyOCR test 9.09 / 13.19 / 34.04 / 58.55 / 22.0 min. All files had a seconds field; detector-size counts matched earlier notes (test 98/1/1, holdout B 393/6/1).
READING: Paddle about 1.4-1.6x faster at the median, 1.7-2x on the mean, 2.3-3x at p90; EasyOCR has a much slower tail.
NOT MEASURED / CAVEATS: only OCR is timed (merge, repair, extractor, validator not timed; the Day 9 demo will time a whole upload). The two engines ran in different runs on a 6 GB machine, so the ratio is indicative only. Crashed Paddle attempts write no file, so their lost time is not in these numbers. It is not known whether the seconds include the smaller-detector retry or model loading after a restart. The slowest test file (31.10 s) is not identified (test indices are not printed).
LLM cost: 1,276 tokens per receipt on average (largest 2,116; 127,650 over 100 train receipts); 0 schema failures; about 20 min per 100 receipts is RATE-LIMIT-BOUND (Pacer for Groq free plan), not model speed; per-call latency was never recorded. Money paid: $0 (free plan). No per-receipt price is quoted (not looked up).


## Day 9: demo (checkpoint; README still to do)

Decisions: 1a rules arm only (v3, adjacent="both", tolerance 1, grounding off; no key, no internet at upload time). 2d verdict wording: red SEND TO REVIEW, green PASSED THE CHECKS, never "OK"; under the green verdict a measured line (500 CORD receipts: 282 without a flag, 1 of them with a wrong total/subtotal/tax/service value; items are not checked); "arithmetic checks that could run: N of 3" with the reason for each check that could not run, in both states. 3b OCR boxes drawn on the photo, coloured by confidence (same thresholds as side_by_side.py), with joined pieces shown in { }. 4b examples load the cached OCR and run every later stage live; the page says so. 5b two columns on a wide screen, one column on a narrow one. 6b one README with collapsible detail blocks.

Built: scripts/ocr_one_image.py (one image, run by .venv-paddle, same record shape as the cache plus load_seconds and detector_side_used, EXIF rotation applied, exit code 3 if every detector size fails); src/pipeline.py (run_ocr as a subprocess with a 120 s timeout and plain failure messages; run_stages with seconds per stage; arithmetic_checks; load_example); src/display.py (banner and table rows, no Gradio, all receipt text escaped); src/overlay.py; scripts/demo_app.py (Gradio 6.31.0; theme/css moved from Blocks to launch() in Gradio 6, not used); demo_examples/ (4 CORD validation receipts at full pixel size, their cached Paddle OCR, a credit file; 0.90 MB). Tests: 157 pass (new: pipeline, display, overlay, a syntax check of the page).
A bug from my own edit (two pairs of lines glued together in demo_app.py) passed all tests because no test imported the page; found by reading the file; test_demo_app_syntax.py now compiles it.

Checks: the new OCR script reproduced the cached result for validation receipt 0 (13 pieces, same texts, same boxes). One receipt only; the fallback sizes were not exercised. A synthetic file (pixels stored sideways, EXIF orientation 6) came out upright on the page, with boxes on the text and the right verdict. Synthetic file, one orientation, not a real phone photo.

Image sizes in the 600 cached Paddle files (long side): median 1296 px, 90 over 2560 px, maximum 4224 px. OCR seconds by band: up to 1280 px 4.6 s (226 receipts); 1281-1600 6.1 s (255); 1601-2048 9.2 s (25); 2049-2560 20.2 s (4 receipts, too few to read); over 2560 13.8 s (90). The demo keeps the 2560 cap and the 1600/1280 fallbacks of the measured pipeline.

End-to-end timing (first live upload, validation receipt 0, one run, 6 GB machine): OCR predict 7.1 s, model loading 12.8 s, whole subprocess 41.1 s. A second upload took about the same (read from a small screenshot). About 20 s of the 41 s is outside the two OCR timers and was NOT broken down (Python start-up, Paddle import, teardown, or other). Stages after OCR in the same run: merge 1.6 ms, repair 6.2 ms, extractor 3.0 ms (includes its own merge and repair), text for the validator 1.4 ms, validator 1.2 ms. The merge and repair figures are run once for display; the extractor and the validator text each run them again inside.

Examples (validation indices, which are used up for development): 0 passes the checks (2 of 3 ran, total 45,500, label 45,500). 16 caught: the amount column sits one row below its labels, so the cash amount is read as the total (100,000 vs label 20,000; gap 80,000; confidence 0.9938). 66 total not readable: both amounts print with a leading dot (".7,000", refused by the normalizer) and the paper says TL; the TL line is also absent from the repair table, cause not traced. Probably two separate problems, not one. 7 queued although all four headline values are right: the discount line (-9,545) is taken as an item, so items vs subtotal differ by 9,545 (found-not-fixed: no discount field).

Not measured: whether Gradio makes other network calls (anonymous analytics are switched off); other EXIF orientations; real phone photos; any receipt that is not from CORD.
