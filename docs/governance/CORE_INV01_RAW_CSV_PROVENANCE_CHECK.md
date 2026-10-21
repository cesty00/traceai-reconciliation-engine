# CORE INV-01 — Real raw CSV provenance checkpoint (2026-10-21)
Status: RAW-SOURCE ROWS VERIFIED INDEPENDENTLY / CORE POINTER INTEGRATION OPEN

## Immutable raw-file source check
- Authorized original: Trasabilitate_WMS_2025-12-15_2026-10-11_export_2026-10-11.CSV.
- SHA-256 exact bytes: `98e1a88a438d41ff7dda555d8a77f675fd9b2cf6736a636fc5c75bf13c377ece`.
- CSV physical start rows: 351551 (-131.75 kg, FDT250730-64, INV-MIN), 351552 (-0.25 kg, FDT250730-72, INV-MIN), 351553 (+45.65 kg, FDT250730-58, INV-PLS), article DS099904440, document `00060`, date 2026-10-10. Signed net -86.35 kg.
- The previously generated local patch `case.json` records the **same** `investigation.source_hashes.wms_movements` and preserves document `00060`, lot and quantities inside `inventory_adjustment_matching.residual_wms_adjustments[].contributing_event_refs`, but still records `source_pointer_status: UNVERIFIED`. Raw line 351551–351553 are NOT carried into these runtime refs.
- Reported signed delta -86.35, explained -86.35, residual 0 and verdict REVIEW remain unchanged.

## Critical causal ownership distinction
- INV-01 effect is calculated from **all** unmatched inventory WMS residuals minus unmatched WME PV residuals.
- For this case: `residual_wms_total = +74.46` kg, `residual_wme_total = +160.81` kg, therefore `system_difference_effect = -86.35` kg.
- WMS document `00060` independently nets -86.35 kg. This numerical equality DOES NOT prove that the matcher attributed the entire INV-01 effect uniquely to `00060`; other residual inventory events exist and cancel in aggregate.
- Do not label a single document as the exclusive mathematical cause without a verified allocation/ownership proof.

## Remaining acceptance criteria
1. Bind immutable source hash + raw physical start row + exact document/article/lot/quantity into each contributing event; fail closed on mismatch/stale file.
2. Prove the ownership and exclusion/matching of other WMS inventory and WME PV events, with no double attribution (GOV-AT-05/06).
3. Expose only verified refs in operator-facing JSON/DOCX with separate human reason and economic REVIEW.
4. Run exact-head controlled regression and complete governance review before merge.
No raw client CSV/XLSX files committed. No CORE mutation or merge; GOV-002/GOV-AT-05/06 OPEN, V1 NO_GO.
