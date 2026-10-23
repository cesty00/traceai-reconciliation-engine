# GOV-C4.2 — Frozen CORE QA inventory (2026-10-23)

Baseline code commit: `e8e9009285a8c7874b05967733089968abaa3309`.
Method: **direct GitHub file reads at this exact SHA** and inspection of selected `test_*` names and assertions. No pytest execution and no CI status for this SHA obtained in C4.2. Presence of tests is not proof of pass, adequate breadth, or real-source acceptance.

| Family | Existing test file at baseline | Example positive and negative test evidence | Status |
|---|---|---|---|
| RECEIPT | tests/test_receipt_matching.py (7 tests) | supplier FE match; quantity discrepancy remains residual; transfers/returns outside scope; FE preferred over F | TEST_FOUND; EXECUTION_UNKNOWN; OPERATOR_VALIDATION_OPEN |
| DELIVERY | tests/test_delivery_matching.py (13 tests) | net delivery-return chain; quantity difference; cancellation and duplicated-event guards | TEST_FOUND; EXECUTION_UNKNOWN |
| RETURN_IN | tests/test_delivery_matching.py | RET_WME matching positive AE; supplier receipt not classified as customer return | TEST_FOUND; EXECUTION_UNKNOWN |
| TRANSFER MOSE | tests/test_transfer_mose_matching.py (10 tests) | direct match / short-lag unique; ambiguous same-day qty not forced; basket disambiguation | TEST_FOUND; EXECUTION_UNKNOWN; G3 NOT ACCEPTED |
| BC | tests/test_production_input_matching.py (8 tests) | PRODUCTION-IN vs BC; qty mismatch REVIEW; other-order correction not reused | TEST_FOUND; EXECUTION_UNKNOWN |
| NP | tests/test_production_matching.py (16 tests) | reversal/order correction and positive non-production guard; ambiguous post-NP stays REVIEW | TEST_FOUND; EXECUTION_UNKNOWN |
| INVENTORY/PV | tests/test_inventory_adjustment_matching.py (3 tests) | unique inventory pair; aggregated same-day rows; ambiguous PV not forced | TEST_FOUND; EXECUTION_UNKNOWN |
| COR STOC ADJUSTMENT | tests/test_stock_correction_matching.py (1 test) | exclude production/special locations; **no verified offset-pair regression test in this file** | TEST_FOUND; GAP DEF-G1-001 OPEN |
| OPENING | tests/test_opening_stock_policy.py (3 tests), tests/test_investigation.py (8 tests) | present/missing opening; absence is unknown by default; separate opening difference | TEST_FOUND; EXECUTION_UNKNOWN; WME StocInitial semantics unverified |
| ZONE / WAREHOUSE | tests/test_stock_report_zone_matching.py (5 tests); tests/test_special_status_matching.py (2 tests) | zero totals hide zone differences; special status requires WME quantity evidence | TEST_FOUND; EXECUTION_UNKNOWN |
| WME RESIDUAL | tests/test_wme_residual_matching.py (2 tests) | unpaired special stock movements; special warehouse exclusions | TEST_FOUND; EXECUTION_UNKNOWN |
| SOURCE PROVENANCE | tests/test_source_provenance.py (2 tests) | semantic source paths, operator provenance contract | TEST_FOUND; EXECUTION_UNKNOWN |
| PIPELINE/DAILY | tests/test_investigation.py; tests/test_daily.py | DOCX/case model, REVIEW for missing mapping, daily input fail-closed, idempotency | TEST_FOUND; EXECUTION_UNKNOWN |

Counts indicate functions named test_ in the exact files read, not an exhaustive test suite census. Also, labels such as `test_real_product_pipeline_builds_case_report` may use synthetic fixtures; do not equate with authorized company raw source validation.

## Confirmed QA gaps
1. No fresh `pytest` run or CI run verification performed on baseline candidate SHA. All statuses are TEST_FOUND / NOT_RUN_IN_C4.2.
2. `tests/test_stock_correction_matching.py` covers special-location filtering, not hypothetical +/- offset semantics; DEF-G1-001 requires negative false-pair regression before implementation.
3. Neither discovered unit tests nor their name establish unique economic-event ownership across matchers, all document families, same management scope or operator sign-off.
4. Need actual source-backed fixture inventory and full-population census tied to SHA, including case DS099904670 and 20011.

## Prioritized next controlled step
C4.3: enumerate frozen baseline test suite using tree/checkout or CI artifact; run focused `pytest` for receipt/delivery/returns/BC/NP/inventory/adjustments/opening, record environment, exact exit code, failures, SHA. Then build separate source-backed acceptance matrix. No CORE code change approved.

This is a QA inventory only. G0 OPEN / G1 READ_ONLY / CORE NO_GO.
