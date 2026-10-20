# GOV-002Y — Read-only provenance adapter implementation gate

Date: 2026-10-20
Decision: CONDITIONAL GO FOR A SEPARATE IMPLEMENTATION PROPOSAL; NO_GO FOR RUNTIME INTEGRATION / MERGE
Scope: CORE only, not MOSE or EXT.

## Evidence
- CI #1252 (Draft PR #61, synthetic freshness and ambiguity test-only wrapper): completed SUCCESS, `583 passed, 1 xfailed, 4 warnings`.
- CI #1249 (Draft PR #60, candidate row-set prototype): SUCCESS, `579 passed, 1 xfailed, 4 warnings`.
- CI #1244 (Draft PR #59, WMS/WME original-row provenance): SUCCESS, `575 passed, 1 xfailed, 4 warnings`.
- GOV-002S/T/V design audits detail existing `SourceRowNumber`, index SHA, matcher document aggregation, CaseReport/DOCX/operator boundaries.
- One expected xfail still represents unproven `EventOwnershipLedger` wiring into CORE, not a success.
- All validation above is synthetic, within test-only code. No authorized real-source operational UAT has been completed in this gate.

## Implementability decisions

| Gate | Status | Explanation |
|---|---|---|
| Synthetic physical row + SHA identity | PASS (scoped) | Indexed WMS/WME fixtures, multiple source rows |
| Stale WMS and WME index rejection | PASS (test-only) | Experimental wrapper calls `is_current`; runtime has no such adapter yet |
| Duplicate row / missing coordinates / multi-product ambiguity | PASS (test-only) | Conservative candidate refusal in test prototype |
| Exact source-to-document identity in every matcher | OPEN | Existing matcher aggregates omit source lines; document equality alone insufficient |
| Backward-compatible CaseReport/DOCX/UI propagation | OPEN | Inspected statically; no running integration test |
| Real inter-matcher double-claim prevention (GOV-AT-05/06) | OPEN | Existing ledger unit guard and xfail, not verified in orchestrator |
| Authorized real-source operator UAT | OPEN | Mandatory before release |
| Runtime security, rollback, performance and full regression | OPEN | Must be demonstrated after implementation exists |

## Decision and allowed next action

Recommend **authorizing a narrowly scoped implementation-design PR** only (specification, tests and minimal adapter contract) as the next step, subject to owner approval before modifying CORE runtime. The smallest potential runtime change is an additive, read-only module; no automatic MATCH, economic impact aggregation, stock mutation, change to matcher signatures, DOCX or operator decisions.

Before implementation, define:
1. Definitive input: index instance, original source paths, current hashes and a typed document candidate; index must be current on every candidate resolution.
2. Output: `COMPLETE|PARTIAL|UNAVAILABLE`, explicit WMS/WME source keys, SHA-256, physical row numbers, reason and non-authoritative evidence classification.
3. Fail closed on stale index, missing provenance, duplicate source IDs, quantity mismatch, ambiguous product/document/warehouse, and unsupported operation family.
4. Regression set: all existing tests, negative cases, no source writes, rollback of entire isolated module, no user-facing change until explicitly reviewed.
5. Explicit future go/no-go after isolated implementation, prior to any engine/report/streamlit wiring. UAT and GOV-AT-05/06 remain separate later gates.

**No approval to modify CORE production code is implied by successful test-only CI or this recommendation.** Draft PR #56–61 remain unmerged. GOV-002 OPEN, V1 NO_GO.
