# GOV-002C — CORE dependency matrix
Date: 2026-10-19. Status: IN PROGRESS. Candidate test files are NOT verified coverage.

Comparison main...MOSE: 27 modified package Python paths plus operator_app.py (28 CORE/operator paths). No code changes authorized.

| Risk group | File | Candidate tests to inspect | Acceptance |
|---|---|---|---|
| ORCHESTRATION | `src/traceai_reconciliation/investigation/engine.py` | test_investigation.py; test_daily.py; test_artifact_gate.py | OPEN |
| ORCHESTRATION | `src/traceai_reconciliation/investigation/daily.py` | test_investigation.py; test_daily.py; test_artifact_gate.py | OPEN |
| ORCHESTRATION | `src/traceai_reconciliation/investigation/self_service.py` | test_investigation.py; test_daily.py; test_artifact_gate.py | OPEN |
| ORCHESTRATION | `src/traceai_reconciliation/investigation/case_builder.py` | test_investigation.py; test_daily.py; test_artifact_gate.py | OPEN |
| ORCHESTRATION | `src/traceai_reconciliation/investigation/case_publication.py` | test_investigation.py; test_daily.py; test_artifact_gate.py | OPEN |
| ORCHESTRATION | `src/traceai_reconciliation/investigation/artifact_gate.py` | test_investigation.py; test_daily.py; test_artifact_gate.py | OPEN |
| PROVENANCE | `src/traceai_reconciliation/investigation/source_index.py` | test_g1_source_row_provenance.py; test_g1_daily_case_provenance.py | OPEN |
| PROVENANCE | `src/traceai_reconciliation/investigation/daily_case_provenance.py` | test_g1_source_row_provenance.py; test_g1_daily_case_provenance.py | OPEN |
| PROVENANCE | `src/traceai_reconciliation/investigation/daily_provenance_report.py` | test_g1_source_row_provenance.py; test_g1_daily_case_provenance.py | OPEN |
| PROVENANCE | `src/traceai_reconciliation/investigation/bc_index_bridge.py` | test_g1_source_row_provenance.py; test_g1_daily_case_provenance.py | OPEN |
| PROVENANCE | `src/traceai_reconciliation/investigation/bc_row_link.py` | test_g1_source_row_provenance.py; test_g1_daily_case_provenance.py | OPEN |
| PROVENANCE | `src/traceai_reconciliation/investigation/human_evidence.py` | test_g1_source_row_provenance.py; test_g1_daily_case_provenance.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/economic_event_ledger.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/operation_timeline.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/delivery_matching.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/production_input_matching.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/wme_residual_matching.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/stock_report_zone_matching.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/cor_stoc_pv_candidates.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| ECONOMIC | `src/traceai_reconciliation/investigation/delta_movement_window.py` | test_economic_event_ledger.py; test_investigation.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/investigation/operator_report_registry.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/investigation/operator_status.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/reports/docx_report.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/reports/operator_causes_report.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/local_source_detection.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/operator_pilot_matrix.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `src/traceai_reconciliation/operator_stock_view.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |
| OPERATOR | `operator_app.py` | test_g1_daily_provenance_docx.py; test_human_attestation_registry.py | OPEN |

## Directly observed dependencies
- engine.py imports source_index_policy, core matchers, operation_timeline, source readers and cor_stoc_pv_candidates, not client_config or new mose_control directly.
- mose_control/mose_source_index.py imports SQLiteSourceIndex and PRIVATE _csv_chunks/_fingerprint from core source_index.py. Potential upgrade coupling.
- daily.py imports daily_case_provenance and self_service; operator_app.py imports CORE registry, status, stock views and loaders.
- docx_report.py and operator_causes_report.py both import report_model.

## Limits and gates
- Filename-based test assignment is a planning lead only; inspect tests and execute them before calling coverage verified.
- The 321-commit dependency history, indirect imports and real data acceptance still require inspection.
- Preserve mixed PR #56 as Draft; no cherry-pick, merge or deletion until approved cut plan.
- The next step GOV-002D inspects P0 test contents and commit-change boundaries, then proposes an extraction sequence.
