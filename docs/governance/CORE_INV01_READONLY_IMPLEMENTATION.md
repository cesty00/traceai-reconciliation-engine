# CORE INV-01 controlled patch — 2026-10-21
Status: DRAFT / NOT MERGED / V1 NO_GO

Approved read-only additive patch to inventory_adjustment_matching.py. WMS unmatched grouped adjustments now include `contributing_event_refs` each with document, lot, date, reason, quantity and `source_pointer_status=UNVERIFIED`. No SHA, physical source row, economic identity or operator validation is invented. Existing grouping, WME PV match, net effect and verdict are untouched. Three synthetic regression tests added.

The `engine.py` already passes matcher `residual_wms_adjustments` into `details.inventory_adjustment_matching`; no extra engine change needed to retain these new fields in that details structure. This does NOT yet put source refs into the `auto_explain` component nor prove their provenance in operator JSON/DOCX. Prior INV-01 causal-provenance xfail remains unresolved on the documentation branch. Global event ownership GOV-AT-05/06 OPEN, GOV-002 OPEN. Next: verify new PR CI and run controlled six-source real-case regression; obtain separate approval before further runtime wiring/merge.
