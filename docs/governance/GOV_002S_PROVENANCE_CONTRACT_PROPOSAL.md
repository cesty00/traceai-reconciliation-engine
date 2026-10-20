# GOV-002S — Proposed minimal source provenance and economic ownership contract

Date: 2026-10-20 | Status: PROPOSAL ONLY / NO IMPLEMENTATION APPROVAL

## Verified baseline
- CI #1238 on test-only PR #58 commit d060e772: 573 passed, 1 xfailed, 4 warnings; four workflow jobs SUCCESS.
- GOV-002R synthetic CORE SQLite index WMS CSV/WME XLSX/production CSV verifies physical WMS row 2, WME row 3, source SHA-256, original files unchanged.
- Receipt matcher returns a document-level MATCH without a per-row source claim.
- Economic ledger unit guard exists separately; one strict xfail remains documenting no demonstrated engine-level use. GOV-AT-05/06 OPEN.

## Candidate data contracts (unimplemented)
**SourceLineIdentity:** `system: WMS|WME|PRODUCTION`, `source_key`, `source_sha256`, `physical_row_number`. `source_key` specifies the exact indexed source; physical row must be obtained from the source reader/index, not a DataFrame index. The current EventOwnershipLedger.SourceLine supports only WMS/WME; adding PRODUCTION requires separate compatibility consideration.

**MatcherEvidenceClaim:** `matcher_id`, `document_key`, `candidate_source_lines`, `interpretation: CONFIRMED|REVIEW`, `proposed_delta_wms_minus_wme`, `evidence_references`, `provenance_status: COMPLETE|PARTIAL|UNAVAILABLE`. Aggregates must list all source rows or explicitly mark missing provenance. Document number alone does not imply ownership of every row.

**Ownership resolution:** One physical source line may appear in several REVIEW perspectives. A confirmed contribution may be registered at most once; if two CONFIRMED candidate events share one source line and conflict, fail closed to REVIEW/blocked pending evidence; never sum twice, silently discard, or force MATCH. A source claim is distinct from a proposed net economic effect; zero-impact neutralized document pairs still need explicit semantics.

## Preconditions for safe integration
1. Inventory all matcher output types and their provenance, including WMS, WME, production and opening balance; avoid inventing row identities.
2. Create source-file-backed tests with two real matching paths able to claim the same physical source row, if reachable.
3. Assert explained + unexplained = initial delta; reject duplicate confirmed effects and preserve unresolved amount, status and evidence in generated case report.
4. Ensure compatibility with existing CORE daily, DOCX, operator UI, index cache and synthetic regression suite; source hashes must be current.
5. Run authorized real-source read-only E2E and operator acceptance separately, without exposing original data in public demo/tests.

## Decision and status
**No CORE change is approved by this document.** An implementation PR requires explicit architectural agreement and proven behavioral acceptance scenario. GOV-002 OPEN; GOV-AT-05/06 OPEN; V1 NO_GO. Draft PRs #56/#57/#58 remain unmerged.
