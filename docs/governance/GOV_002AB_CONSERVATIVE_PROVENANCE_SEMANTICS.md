# GOV-002AB — Conservative provenance semantics decision

Date: 2026-10-20. Status: DESIGN DECISION; NOT A RUNTIME CHANGE.

## Verified test evidence
GitHub Actions #1263 at GOV-002AA test commit b55c7746: 593 passed, 1 xfailed, 4 warnings; all four jobs SUCCESS.

Adversarial synthetic scenarios demonstrate the current read-only supplier-receipt provenance adapter can return COMPLETE for a WMS 6+4 vs WME 7+3 split, or for a document involving multiple WME warehouses. COMPLETE currently establishes candidate source row identities, not individual row correspondence, lot equivalence, warehouse correctness, or economic confirmation.

## Contract decisions
1. Replace ambiguity of the label with a more explicit future output distinction: `SOURCE_SET_IDENTIFIED` (all candidate physical rows located) versus `OPERATION_EQUIVALENCE_CONFIRMED` (requires independent domain controls). Existing COMPLETE must **never** imply the latter.
2. Warehouse mismatch, missing warehouse linkage, mixed lots, split receipts, reused document across unrelated families or products: retain REVIEW for operational-equivalence verdict until separate evidence and rules establish correspondence.
3. Do not force one-to-one pairing when WMS and WME granularity differs. Preserve multiple physical source rows and document-level quantities, separately reporting gaps.
4. Missing or stale source files, SHA changes, duplicated or unresolvable physical coordinates: provenance UNAVAILABLE; block use as confirmed claim.
5. Only the ownership controller can decide confirmed economic impact, after independent evidence; current adapter has no such responsibility.

## Implementation choice
DO NOT alter existing engine.py, matcher signatures, case reports, operator UI or calculations in this checkpoint. PR #62 (isolated module) and PR #63 (characterization tests) remain Draft and unmerged.

Next required gate: determine with the owner whether a backward-compatible richer provenance result type is wanted in isolated adapter PR #62, then write tests for semantics before changing runtime API. Approval for isolated adapter development does NOT authorize whole-engine integration. GOV-AT-05/06 and GOV-002 OPEN, V1 NO_GO.
