# CORE-UAT-04H — Six-role implementation readiness review
Date: 2026-10-21
Status: DESIGN REVIEW COMPLETE / CORE CHANGE NOT AUTHORIZED
Baseline: commit 24e72be1; CI #1379 completed SUCCESS (pytest, daily-release-gate, release-readiness-gate, release-candidate-gate).

## Role assessments
1. Architecture — CONDITIONAL GO for a dedicated CORE-only patch branch, preserving matcher public fields and leaving the existing PR #67 Draft. NO_GO for runtime integration absent proven immutable pointers and versioned output.
2. WMS/WME specialist — Source WMS adjustment documents may have multiple lots/reasons and same-day events. Current grouping by day/reason must remain unchanged. WME PV match/neutralization is not a blanket accounting equivalence; the actual stock scope matters. CONDITION: retain all contributed documents in each grouped residual.
3. Stock Controller — For DS099904440 snapshot 2026-10-11 20:00, doc 00060's three lines net -86.35 kg; reason is operator-confirmed inventory only for that document. No auto-WME adjustment. 4.40 kg WME warehouse-scope issue remains separate.
4. QA — CI green proves old synthetic regression set, not new source-backed event attribution. Require tests for two docs same day/reason, multiple lots, WME PV neutralization, SHA stale, duplicate ownership, legacy JSON/DOCX, operator status semantics and source-backed real case; current strict xfail must not silently become xpass.
5. Data/BI — Original warehouse/source export identifiers are data lineage. Index/DataFrame row positions cannot substitute physical source rows. Record immutable SHA/worksheet/physical coordinate as verified or UNVERIFIED explicitly.
6. Product Management + Security/IP — Read-only, minimal operator utility first. Confidential source records not in repository, exports or demo artifacts. No licensing/IP changes and no merge into CORE without explicit decision.

## Decision matrix
- CI baseline: PASS (#1379).
- Real 00060 source arithmetic: PASS as independent audit; actual CORE numeric output reproduced.
- Source pointer in current CORE INV-01 explanation: FAIL (not implemented).
- Global non-double-counting GOV-AT-05/06: OPEN.
- Legacy report compatibility for proposed change: UNTESTED.
- Operator validation UAT for proposed change: UNTESTED.
- CORE implementation approval: NOT GRANTED.
- V1 Daily Release: NO_GO.

## Next approved-for-preparation scope (no production changes)
Create a dedicated CORE-only proposal branch from vetted CORE baseline, carry only synthetic regression fixtures and a narrowly scoped proposed patch diff for review, if separately authorized. Before integration, show exact changed files, economic invariants, test results and rollback plan. Keep PR #67 draft and source backed pilot evidence as documentation.

## Explicit user approval needed before implementation
Approve specifically a *read-only additive CORE implementation* of contributing event references, limited to inventory matcher / investigation propagation and tests, with no automatic posting, no forced economic MATCH, and no merge. Generic continuation is not treated as approval of a previously designated separate approval gate.
