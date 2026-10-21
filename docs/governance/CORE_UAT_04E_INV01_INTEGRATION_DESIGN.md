# CORE-UAT-04E — INV-01 minimum integration design and decision gate
Date: 2026-10-21
Status: DESIGN / NO CORE IMPLEMENTATION AUTHORIZED

## Verified execution path
1. `investigation/engine.py` (approximately line 991) invokes `match_inventory_adjustments(wms_rows, wme_rows)`.
2. `inventory_adjustment_matching.py` groups WMS candidates by `(_day, _reason)`; only group day, reason, sum and row count are retained. WME PV groups have document and DataFrame indices.
3. `residual_wms_adjustments` returns `{date, reason, quantity, status}`: no WMS document, lot, immutable event key, source SHA or physical row.
4. `engine.py` (approximately lines 995–1014) copies the aggregated matcher result, and around line 1069 may include its net in the already-calculated stock delta.
5. `auto_explain.py` (approximately lines 431–451) uses this net to create the generic `INV-01` component. Adding a document ID solely in auto_explain would be unverifiable: the matcher has already discarded it.

## Proposed minimal production change (requires separate approval)
- Make a **versioned additive** field on each matcher residual group, e.g. `contributing_event_refs`, preserving the existing `date/reason/quantity/status` schema and calculations.
- The event refs originate from raw rows before grouping: original source-file SHA, verified physical coordinate, system, document, article, lot, date, operation, signed effect and unique economic event ID. Never infer source line from a DataFrame index or SQLite rowid; until a source pointer is independently verifiable, include an explicit `UNVERIFIED/REVIEW` indicator, not fabricated source IDs.
- Preserve original `match_inventory_adjustments` sums, matching/neutralization and economic statuses byte-for-byte in a regression comparison. Retain document grouping semantics as currently defined unless separate business UAT approves a change. A single group may include multiple documents; show them all, not one guessed document.
- Carry structured refs through `engine.result.details.inventory_adjustment_matching` into a versioned operator-facing evidence annex and DOCX extension. Do not encode document IDs only inside free text or silently change existing `ExplanationComponent` consumers.
- Explicitly check source-staleness, group-sum identity, partial allocation and global one-event-one-owner across delivery/return/production/inventory matchers; GOV-AT-05/06 stays OPEN until proved.
- Legacy CaseReport schema and existing DOCX report must remain readable; generate an additive appendix only after evidence and operator permission gates. Keep original human-review, no mutation and no automatic MATCH.

## Exact real UAT case
DS099904440, snapshot 2026-10-11 20:00: WMS 00060 on 2026-10-10 includes three distinct rows (-131.75,-0.25,+45.65), net -86.35; reported WMS-WME -86.35. Operator separately identified this document as inventory. Core engine already returns INV-01, EXACT, residual zero and REVIEW but without structured document linkage. WME multi-warehouse delta 4.4kg is a separate issue and must not alter this claim.

## Proposed acceptance gates
A1: test source refs survive grouping for two distinct WMS documents of same date/reason and with multiple lots.
A2: match and residual economics unchanged, including already matched WME PV pairs.
A3: immutable source provenance verified independently; stale/ambiguous refs fail closed.
A4: one event can have only one economic causal owner across all matcher families.
A5: source-backed CORE run produces 00060 and all three line references in structured operator output and addendum DOCX, while verdict remains REVIEW and mutation flags false.
A6: old report output still passes compatibility contract; unknown operator reason remains REVIEW.
A7: no WME correction is ever generated automatically.
No implementation/merge without explicit per-SHA approval; GOV-002 / GOV-AT-05/06 OPEN; V1 NO_GO.
