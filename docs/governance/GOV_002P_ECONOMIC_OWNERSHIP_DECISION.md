# GOV-002P — Economic ownership coverage decision matrix

Date: 2026-10-20. Status: REVIEW COMPLETED; GOV-AT-05/06 OPEN; V1 NO_GO.

## Baseline observed
- Draft PR #58 remains OPEN/DRAFT, unmerged, head `9b2a43dffaaec98d9b91bf4ba4cd40f032db5993`, based on GOV-002H test branch.
- GitHub Actions #1231 at that commit COMPLETED/SUCCESS, pytest log previously verified: `572 passed, 1 xfailed, 4 warnings`.
- No feature/production CORE code edited in GOV-002K..O.
- The strict xfail in `tests/test_gov_002k_economic_ownership_characterization.py` checks a literal `EventOwnershipLedger` reference in `investigate_product`. This is a *wiring signal*, not a behavioral ownership test, and is not release acceptance.

## Evidence and remaining gaps

| Criterion | Confirmed evidence | Not demonstrated | Decision |
|---|---|---|---|
| GOV-AT-05 | Standalone ledger blocks two CONFIRMED events claiming identical `SourceLine`. GOV-002L and N exercise actual matcher interaction; GOV-002O runs actual engine with synthetic sources. | A source-file-backed case where TWO CORE matcher paths independently propose confirmed impact for the SAME physical source row, with an engine-level global ownership check. | PARTIAL / OPEN |
| GOV-AT-06 | Standalone ledger REVIEW contribution is zero, then CONFIRMED contributes once. WME residual movements stay labelled REVIEW in synthetic tests. | Shared physical row identity and status propagation REVIEW+CONFIRMED through the actual engine and source-backed provenance, across matchers. | PARTIAL / OPEN |
| GOV-002L | #1220 SUCCESS: receipt FE/F exact quantity excluded from residual; mismatch remains visible as REVIEW. | All alternative operation families or original file coordinates. | LOCAL PASS |
| GOV-002N | #1226 SUCCESS: matched inventory PV excluded from residual; mismatch visible as REVIEW. | Cross-family economic uniqueness in complete engine. | LOCAL PASS |
| GOV-002M | #1223 SUCCESS: synthetic source-backed unresolved product case remains REVIEW; arithmetic balanced and sources unchanged. | Cross-matcher duplicate claim scenario. | SCENARIO PASS |
| GOV-002O | #1229 failed due missing synthetic WMS `Lot`; fixture-only correction; #1231 SUCCESS. Synthetic -10 INV-MIN / -9 PV; REVIEW and arithmetic checks. | Full `SourceLine` identifiers fed into ownership ledger across engine matchers. | SCENARIO PASS |

## Architectural decision

Do not claim a proven double-accounting defect, nor claim global protection. Existing engine applies local eligibility and exclusion rules; these are meaningful but are not equivalent to a proven canonical per-line ownership invariant. A green CI (even release-candidate-gate) is not operational UAT acceptance.

## Next controlled step: GOV-002Q

1. Instrument a **test-only** synthetic probe at the engine boundary. Capture per-matcher candidate economic effects and exact source identities when the production APIs actually expose them. Do not invent physical source rows by substituting DataFrame indexes.
2. Build an evidence matrix of which matcher outputs identify physical rows versus only document aggregates. Identify whether duplicate confirmed claims are feasible from the actual filtering logic. If no overlap is feasible in scoped case, report "not reproduced", not "fixed".
3. If actual overlap is reproduced, preserve a failing regression with source SHA + physical row coordinates, final explained/unexplained balance, and REVIEW fail-closed expectation. No production intervention before evidence and explicit approval.
4. After behavioral evidence, decide if EventOwnershipLedger must be wired into `investigate_product` or if existing disjoint ownership can be proven and enforced via a smaller contract.
5. Keep PR #56/#57/#58 Draft/unmerged, GOV-002 OPEN, V1 NO_GO pending separate MOSE/CORE, original-source operator UAT and release gates.

No changes to CORE runtime or merges authorized by this document.
