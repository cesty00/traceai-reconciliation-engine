# CORE-UAT-04G — Controlled CORE change proposal (approval gate)
Date: 2026-10-21
Status: DESIGN ONLY. NOT IMPLEMENTATION APPROVAL.
Baseline: CORE-UAT-04F at af3127c5; CI #1375 completed SUCCESS (all four jobs).

## Exact minimal code change requested for subsequent approved phase
1. In `src/traceai_reconciliation/investigation/inventory_adjustment_matching.py`, retain an **additive audit-only** list for each WMS (_day, _reason) group, derived *before* aggregation, containing Document, Lot, date, reason and signed quantity; attach to `residual_wms_adjustments` as `contributing_event_refs`. Preserve grouping and matching by day/reason, WME PV neutralization, net, tolerance, statuses and original return fields.
2. Do not fill raw physical line, SHA, or immutable event key by guessing from DataFrame index or SQLite rowid. Mark missing source provenance `UNVERIFIED` until separately bound against original WMS bytes and source index with an explicit provider.
3. In `engine.py`, propagate the additive `contributing_event_refs` through `result.details.inventory_adjustment_matching` without changing explained/unexplained quantities, verdict, global event ownership or status.
4. For `auto_explain.py` do NOT imply `SOURCE_ROW_VERIFIED` or `OPERATOR_VALIDATED` solely because a document number is present. Presentation should show pending references and only render verified links after source proof. Prefer versioned additive operator-facing JSON and DOCX annex, keeping historical CaseReport documents valid.

## Exact regression gate before any change may be promoted
- Existing matcher output economic projection must equal baseline exactly: matches, residual totals, system_difference_effect, matched_wme_indexes and statuses.
- Synthetic distinct document IDs for the same day/reason remain distinct in sidecar while total is unchanged.
- Pair with matching WME PV must neutralize exactly as before; ambiguous candidates stay REVIEW.
- Document missing/unverified source line stays UNVERIFIED and cannot be claimed causal proof.
- Enforce GOV-AT-05/06 global no double attribution, including overlaps with delivery/return and production. Do not mark these resolved merely from local prototype tests.
- Controlled real six-source case DS099904440, stock report 2026-10-11 20:00, must reproduce -86.35 kg from 00060's three movements and keep REVIEW, without authorizing WME posting.
- Verify legacy JSON and DOCX schema compatibility, operator field meanings and security of source pointer visibility.
- CI, exact SHA review, human/operator UAT, and explicit approval required before any merge. No licensing/IP change.

## Decision
GO for **reviewing the proposed constrained patch scope**. NO_GO for production CORE implementation/merge until explicit approval. GOV-002 OPEN, GOV-AT-05/06 OPEN, V1 Daily NO_GO.
