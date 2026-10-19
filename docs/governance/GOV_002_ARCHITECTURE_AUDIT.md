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
