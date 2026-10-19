# GOV-002D — Critical tests and dependency verification
Date: 2026-10-19
Status: PARTIAL VERIFIED STATIC REVIEW; CORE MIGRATION NOT APPROVED.

## Scope and evidence
Reviewed test source directly on feature/mose-control-arch01-isolated, head `6a9d0a6e002d6d890b9589627ec698a3b04f5760`. Observed associated workflow #1189 SUCCESS. Did not personally execute tests with original source exports; tests reviewed below contain controlled fixtures rather than production acceptance.

| Component | Test file inspected | Direct evidence from test functions | Remaining critical gap |
|---|---|---|---|
| engine.py | tests/test_investigation.py (443 lines; 9 named tests) | Full case report test, WME mapping absence REVIEW, opening difference handling, BC product investigation | Not independently verified against original full-source E2E; no proof all operation families covered |
| daily.py | tests/test_daily.py (578 lines; 7 named tests) | Manifest/summary, reuse idempotency, missing source fails closed, run-store integration | Source-backed operational acceptance, cross-document causal tracing |
| source_index.py | tests/test_g1_source_row_provenance.py (138 lines; 6 tests) | CSV chunk boundary, XLSX physical rows, multiline CSV, malformed row, index reuse, date-window source coordinates | Large original files, exact row/warehouse scope, incremental integrity and MOSE private helper API |
| economic_event_ledger.py | tests/test_economic_event_ledger.py (60 lines; 6 tests) | Duplicate confirmed row ownership rejected, REVIEW impact 0, distinct WMS/WME source identity, event IDs | Whether this ledger governs all matcher-produced confirmed impacts across engine |
| docx_report.py | tests/test_g1_daily_provenance_docx.py (52 lines; 2 tests) | DOCX XML contains source ROW, SHA and name; missing physical row fails closed | Comprehensiveness, business explanation, full operator UAT across families |

## Directly verified limits
- Economic event tests exercise standalone `EventOwnershipLedger`. Presence of the module and tests does **not** establish global ownership enforcement across all matching paths; integration proof missing.
- DOCX provenance test uses synthetic CaseReport/window and checks serialized XML; not a full real operator report acceptance.
- Tests named `test_real_product_pipeline` or `test_four_real_bc_rows` are names, not proof that production files were read during this audit.
- CI #1189 success is confirmed for the branch snapshot, but branch contains CORE, MOSE and EXT together; passing CI does not certify isolated component behavior.

## Release and branching decisions
1. Keep G0/GOV-002 OPEN. No changes to functional files, no cherry-picks or merges, no new features.
2. Next review: inspect exact dependencies and entrypoints for economic_event_ledger in CORE engine, check source_index private helper use by MOSE, identify which tests require the whole mixed branch.
3. Design candidate CORE baseline using measurable acceptability: actual stock source report → document/row traces → delta reconstruction → DOCX → operator confirmation.
4. Do not declare stable CORE or ship externally until source-backed E2E, security and performance gate.
