# GOV-002T — CORE provenance contract compatibility assessment

Date: 2026-10-20
Status: STATIC COMPATIBILITY ASSESSMENT; DESIGN PROPOSAL ONLY

## Inspected source (test/gov-002k-core-double-claim)
- `investigation/models.py`: `ProductInvestigationResult` has `source_hashes`, `details`, `findings`, `operation_timeline`, `unmatched_operations`, `conclusion_traceability` and human-review verdict; no typed economic claim field.
- `investigation/case_builder.py`: constructs `CaseReport` from result data; explicitly emits `SOURCE_ROWS_NOT_VERIFIED; HUMAN_VALIDATION_NOT_ATTACHED` for unresolved BC trace and requires human intervention. No inference of physical coordinates.
- `reports/report_model.py`: `CaseReport` typed fields plus source hashes, provenance-oriented collections, warnings; no per-line ownership evidence contract.
- `reports/docx_report.py`: consumes `CaseReport` and formats existing report sections; adding mandatory fields could break rendering/validation.
- `investigation/source_provenance.py`: `source_paths` and `source_usage` identify source files and operator-facing source metadata, not each economic match claim.
- `investigation/operator_status.py`: append-only human decisions keyed by product/warehouse, independent of matcher provenance.
- `operator_app.py`: read-only Streamlit pilot running existing CORE self-service and report/status flows; must not acquire automatic correction permissions.
- Prior GOV-002Q/R: `source_index.py` preserves `SourceRowNumber`; document-level matcher outputs need separate explicit source-coordinate claims.

## Compatibility and change-risk matrix
| Boundary | Compatibility issue | Proposed least-risk test-first direction |
|---|---|---|
| SQLite index -> matchers | Current `SourceRowNumber` is available in indexed records, but matcher outputs are aggregates; DataFrame index alone is not physical identity. | Introduce a separate optional evidence adapter that resolves exact source lines and current SHA, with unavailable status on ambiguity. |
| Matcher -> engine | Matchers produce differing document/result structures. Extending every signature simultaneously is high-risk. | Characterize one real matching path in isolated tests, then define a backward-compatible adapter before changing engine. |
| Engine -> ProductInvestigationResult | No typed per-source-row ownership claims. A required new field could break callers/serialization. | Optional, default-empty structured evidence field only after tests and approval; no change to initial/explained/unexplained formula. |
| Result -> CaseReport | `case_builder` copies existing collections and hashes, with explicit unverified BC markers. | Keep unverified markers; optional additive evidence section with strict provenance status and no implicit MATCH. |
| CaseReport -> DOCX | Rendering, validation, annexes and existing template rely on established schema. | Snapshot regression of current DOCX; render optional evidence appendix only after source identity verified. |
| CaseReport -> operator UI | Operator sees source/cause/status and makes append-only human decisions. | Surface UNAVAILABLE/PARTIAL provenance as review-only information; no auto approval or mutation actions. |
| Multi-run/index cache | Hashes change with source changes; previous physical rows may no longer refer to same source. | Validate source hash at use time; invalidate stale claims, never silently rebase row IDs. |
| Production source lines | Existing EventOwnershipLedger.SourceLine System Literal includes WMS/WME only. | Resolve PRODUCTION identity and accounting semantics separately before extending enum or ledger scope. |

## Proposed phased acceptance
1. **Design gate:** enumerate all matcher output types and name exact source-row availability, including absent cases; preserve current interfaces.
2. **Test gate:** synthetic index-to-one-matcher optional evidence resolution; exact SHA+row provenance; unmatched remains REVIEW; stale SHA rejected.
3. **Report gate:** optional backward-compatible CaseReport evidence, DOCX/JSON/validator and operator UI tests; preserve existing output for old cases.
4. **Behavior gate:** GOV-AT-05/06 actual cross-matcher competing source-line claims, no double confirmed economic delta, REVIEW fail-closed, arithmetic invariant.
5. **UAT gate:** authorized read-only original-source tests, operator confirmation, no exposure in synthetic demos.

## Decision
**NO CODE IMPLEMENTATION APPROVAL YET.** GOV-002T documents a compatible *approach* based on static inspection; compatibility is not dynamically tested until a dedicated test-only PR is executed. GOV-002 remains OPEN, GOV-AT-05/06 OPEN, TraceAI V1 NO_GO. PR #56/#57/#58 must remain Draft/unmerged.
