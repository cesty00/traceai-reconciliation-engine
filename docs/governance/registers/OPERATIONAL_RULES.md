# Operational rule register (source of truth needs operator sign-off)
| Rule ID | Rule / qualification | Validation | Applies / evidence |
|---|---|---|---|
| RULE-001 | WME operations and WMS counterparts must be identical or demonstrably logically equivalent; never force MATCH with insufficient evidence. | Owner-established project rule | CORE all transaction families; TRACEAI_DEVELOPMENT_PLAN.md |
| RULE-002 | Physical transfers internal to WMS are NOT additional supplier receipts or external customer deliveries; count economic effect only once. | Source-backed case evidence; global economic ownership validation OPEN | CASE-G1-001; GOV-AT-05/06 |
| RULE-003 | An opposite-sign quantity pair on same SKU/lot/location is a **candidate** compensation, not confirmed economic reversal. | Operational interpretation requires documentary human evidence | CASE-G1-002 / DEF-G1-001 |
| RULE-004 | WME invoice 214401 may not have been posted after WMS receipt closure. | HYPOTHESIS ONLY, mentioned by user as possible cause; NOT operator confirmation or engine-derived cause | CASE-G1-001 |
| RULE-005 | WME StocInitial balances on three 2025-12-27 rows must not be summed as receipts. Interpretation of 19279 -> 94279 transition is UNKNOWN. | Source arithmetic verified; economic provenance pending | CASE-G1-002 |
| RULE-006 | An inventory-specific adjustment requires documentary/operator identification: WMS 00060 on 2026-10-10 identified by operator as inventory; this does NOT generalize to every adjustment. | OPERATOR-CONFIRMED for doc 00060 only | CURRENT_STATUS prior GOV checkpoints |
 
Before future implementation, review sign convention, units, article IDs, fiscal vs physical semantics, warehouse boundaries and provenance per rule. New hypotheses start UNVALIDATED.
