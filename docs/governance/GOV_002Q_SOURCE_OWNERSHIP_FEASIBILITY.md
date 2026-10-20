# GOV-002Q — Feasibility audit: source ownership across CORE matchers

Date: 2026-10-20. Status: STATIC CONTRACT GAP CONFIRMED; DOUBLE COUNTING NOT REPRODUCED.

## Scope and branch
Inspected files from test-only branch `test/gov-002k-core-double-claim` (CORE runtime unchanged):
- `src/traceai_reconciliation/investigation/source_index.py`
- `src/traceai_reconciliation/investigation/engine.py`
- `src/traceai_reconciliation/investigation/delivery_matching.py`
- `src/traceai_reconciliation/investigation/production_input_matching.py`
- `src/traceai_reconciliation/investigation/receipt_matching.py`
- `src/traceai_reconciliation/investigation/inventory_adjustment_matching.py`

## Source-backed observations
1. CORE `SQLiteSourceIndex` CSV parsing attaches a `SourceRowNumber` field, representing physical CSV row coordinates. This alone does not mean all matcher outputs include those coordinates.
2. `investigate_product` resolves source index and hashes source files, but in the inspected engine no literal `SourceRowNumber` reference exists; its delivery, inbound, production-input and inventory operations invoke separate matching functions.
3. `delivery_matching.py`, `receipt_matching.py` and `production_input_matching.py` have no explicit `SourceRowNumber`, `source_sha256` or `SourceLine` field names in their module sources; their result schemas are document-level aggregates. This is a **static field-name inspection**, not an exhaustive dynamic provenance test.
4. `inventory_adjustment_matching.py` returns `matched_wme_indexes` and uses DataFrame indexes to exclude already matched WME rows from residual classification. An index is not inherently a physical source-row number nor portable source identity without a verified mapping.
5. Local exclusions tested in GOV-002L/N/O prevent specific double-review classifications but do not establish an invariant for all matching paths.
6. Existing `EventOwnershipLedger` enforces ownership when used, but direct explicit integration in `investigate_product` was not observed; its xfail wiring test is still expected.

## Acceptance gap
Both GOV-AT-05 and GOV-AT-06 remain OPEN. No actual duplicate confirmed economic impact has been reproduced. There is also not yet proof of complete ownership across matcher paths.

## Recommended GOV-002R: test-only evidence contract
- Create fixture with real synthetic WMS CSV and WME XLSX, verify the index carries correct system-specific SHA-256 + **physical** source row coordinates.
- Characterize each matcher output by candidate document and source identifiers. If an output loses provenance, record `PROVENANCE_UNAVAILABLE` rather than inventing ownership from a document number or DataFrame index.
- Only after mapping exists, attempt a genuine competing-claim case and verify the explained/unexplained delta and fail-closed REVIEW.
- Before implementing a CORE API/ledger integration contract, document minimal backward-compatible fields and secure explicit approval.
- Do not merge PR #56, #57 or #58, and do not change CORE production code until evidence justifies it.

Outcome: GOV-002 remains OPEN; V1 NO_GO; no functional code modified.
