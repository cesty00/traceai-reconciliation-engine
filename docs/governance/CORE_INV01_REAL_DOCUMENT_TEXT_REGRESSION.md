# CORE INV-01 — Real-source text document regression (2026-10-21)

Status: LOCAL REPLAY PASS FOR SELECTED INVARIANTS / NOT FULL SOURCE-PROVENANCE ACCEPTANCE

## Inputs and methodology
Used six authorized original exports from 2026-10-11 already available for DS099904440. Replayed CORE investigation on a local copy of the previously tested code with the approved incremental text-import edits from PR #68 applied to source_index.py and source_readers.py. This was a local reconstruction of the relevant patch changes, **not** a byte-for-byte checkout or verification of the entire GitHub head. No source records committed.

## Observed results
- Case DS099904440: initial -86.35 kg, explained -86.35 kg, unexplained 0.00 kg, economic verdict REVIEW.
- Local JSON investigation details now retain document identifier `00060` as a string for three WMS inventory rows, with respective lots FDT250730-64, FDT250730-72, FDT250730-58 and effects -131.75, -0.25, +45.65 kg.
- Operator JSON unchanged from baseline; no new operator-facing verified documentary claim.
- SHA/physical row provenance remains explicitly UNVERIFIED, and auto_explain INV-01 still lacks structured source pointers.
- Numeric computations were unchanged for this one real case, not for all inventory matching scenarios.

## Checks
- GitHub CI #1394 completed SUCCESS all four jobs for previous head `5395760d`.
- The completed local replay tests document text persistence and selected economic invariants but does not prove full git-head parity, WME post-snapshot status, one-event ownership GOV-AT-05/06, or acceptance of a CORE release.
- Next: run exact-head artifact against authorized inputs and test original CSV hash/physical row pointers; verify index cache version changes do not regress other callers. Keep PR #68 Draft, do not merge. GOV-002 / GOV-AT-05/06 OPEN; V1 NO_GO.
