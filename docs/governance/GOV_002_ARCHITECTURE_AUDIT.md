# GOV-002 — Initial architectural audit (2026-10-19)
**Status:** IN PROGRESS / NO CODE REORGANIZATION APPROVED.
**Method:** GitHub compare main...feature/mose-control-arch01-isolated; direct reading of existing V1 docs; branch list. No local end-to-end data execution in this audit.

## Confirmed repository evidence
- main HEAD: `f947dfd509f1956023ce29c8f6fcbe1333657302`.
- MOSE branch HEAD at comparison: `6a9d0a6e002d6d890b9589627ec698a3b04f5760`.
- GitHub compare: 321 commits ahead, 0 behind, 155 modified/added files, ~8660 changed lines.
- File family accounting (paths, not isolated changesets): 28 CORE/operator, 27 MOSE, 9 EXT/demo, 87 tests, 3 docs, 1 project setup.
- Changes to shared CORE include `investigation/engine.py`, `source_index.py`, `daily.py`, `reports/docx_report.py`; MOSE, EXT and operator UI coexist on branch.
- `docs/V1_DAILY_ARCHITECTURE_GAP_AUDIT_2026-10-14.md` flags P0 economic-event ownership, explicit coverage, causal reconstruction gaps and states V1 launch NO_GO.
- `docs/V1_DAILY_INTEGRATED_REQUIREMENTS_2026-10-14.md` specifies ten requirements; operational approval and real E2E are not demonstrated by a green CI.
- `docs/OPERATOR_PILOT_RUNBOOK.md` labels operator interface a pilot, not completed source-backed UAT; highlights large-file performance and security checks.
- Last inspected branch CI on 6a9d0a6e: run #1189 SUCCESS. This does not close any operational acceptance gate.

## Risk register
| ID | Severity | Fact/risk | Required proof |
|---|---|---|---|
| R-001 | HIGH | MOSE branch contains CORE+MOSE+EXT; cannot merge wholesale | Commit/path dependency graph and isolated regression tests |
| R-002 | HIGH | Existing CORE V1 docs say NO_GO | Source-backed product cases across operation families + human signoff |
| R-003 | HIGH | Source provenance and economic-event uniqueness not globally demonstrated | One-event-one-economic-impact tests, no forced match |
| R-004 | HIGH | Real-source E2E/performance and temporary-file protections not signed off | Operator UAT + security review |
| R-005 | MEDIUM | Earlier CI #1160/#1161 failures not explained | Obtain run-specific job logs, record root cause |
| R-006 | MEDIUM | 321 commits are too many to safely cherry-pick blindly | Dependency inventory with approved cut plan |

## Proposed safe split (NOT executed)
1. Freeze feature additions in MOSE mixed branch; preserve existing SHA and Draft PR #56.
2. Characterize CORE against main, identify prerequisite changes; do not assume the 28 shared paths are safe to port.
3. Prepare dedicated CORE integration branch from main *after* dependency mapping, then run full tests and documentary UAT.
4. MOSE follows on a separate branch based on approved CORE baseline; compare WMS transfers, WME NT, invoices, operator review.
5. EXT stays paused on a separate branch/fixture track, synthetic-only.
6. Do not merge or reset PR #56 prior to operator confirmation of the explicit split plan.

## Not established yet
- Exact commit-to-module dependency graph (not reconstructed from 321 commits).
- CI failure logs for #1160 / #1161.
- Whether every existing test is relevant or passes when split.
- Real-source regression coverage and security clearance.

## Dependency assessment — checkpoint GOV-002B, 2026-10-19
Checked import statements and key references on MOSE branch head `6a9d0a6e`.
- CORE `investigation/engine.py` (~1608 lines) imports internal CORE operation matchers and `source_index_policy`; observed **no direct import of `client_config` or the new `mose_control` package**. Existing CORE transfer-MOSE matching is a distinct older CORE module, not proof that the new optional MOSE package is independent.
- MOSE `mose_control/mose_source_index.py` explicitly imports `SQLiteSourceIndex`, `_csv_chunks` and `_fingerprint` from CORE `investigation/source_index.py`. These private helpers create a version-sensitive dependency.
- MOSE `mose_control/dossier_from_index.py` imports several MOSE siblings; `pages/10_Control_MOSE.py` imports MOSE index/review/dossier modules. MOSE feature requires CORE index compatibility and an isolated operator entrypoint.
- EXT `client_config/normalizer.py` imports only `client_config/contract.py` (observed); no direct references to this package in the reviewed CORE engine, CORE daily or operator entrypoint. Isolation looks feasible **but full reverse-reference scan remains outstanding**.
- `operator_app.py` imports shared investigation, loaders, stock view and registry components; therefore pilot UI and shared CORE must be integration tested together.

### Controlled cut sequence — proposal, not executed
1. Freeze PR #56 (Draft), pin SHA, preserve all docs and tests.
2. **CORE baseline**: enumerate 28 shared paths and their test dependencies against main; define expected product-evidence and reporting behavior before porting any code. Particularly review `engine.py`, `source_index.py`, `daily.py`, `docx_report.py`.
3. **CORE candidate branch from main**: move only approved and tested changes. Integration verify source provenance, effect-on-stock uniqueness, zero/negative mismatches, no forced MATCH and DOCX correctness. Do not call acceptance passed from CI alone.
4. **MOSE branch based on approved CORE**: isolate MOSE-only paths; refactor direct usage of private CORE index helpers or pin an explicit adapter contract and test it.
5. **EXT later**: independently move `client_config`, synthetic fixtures and tests after CORE acceptance gate; no production data in examples.
6. Separate PRs reviewed in order, NEVER merge mixed branch wholesale. Retain original PR #56 for historical reference until approved split is verified.

### Additional audit limitations
Static import inspection is not a complete runtime/dependency graph; indirect imports, dynamic loads, hidden sensitive data, behavior, performance and exact per-commit boundary have not been verified. Existing observed green #1189 does not prove isolated branch tests.
