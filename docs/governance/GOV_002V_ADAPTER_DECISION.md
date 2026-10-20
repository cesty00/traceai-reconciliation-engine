# GOV-002V — Architectural decision: provenance association boundary

Date: 2026-10-20 | Decision type: RECOMMENDATION / NOT IMPLEMENTATION APPROVAL
Scope: TraceAI CORE, not MOSE or EXT.

## Evaluated options

| Dimension | A: separate read-only provenance adapter | B: extend every matcher result |
|---|---|---|
| Changes to existing matchers | Low initially; adapter reads indexed rows and existing outputs | Broad, cross-cutting changes |
| Attribution fidelity | Only when a uniquely evidenced row set can be established; otherwise UNAVAILABLE | Potentially stronger at source, but requires each matcher to preserve source identity through aggregation |
| Compatibility with engine, report, UI | Can be trialed separately with optional result and no mutation | Higher risk for serialization, DOCX, daily and regression tests |
| Double-confirmed-impact guard | Not sufficient alone; needs an explicit later ownership decision at orchestration | Not sufficient alone; per-matcher output still needs a shared conflict guard |
| Special cases (splits, reversals, same document reused) | Must refuse ambiguous matches; no quantity-only inference | Can carry exact participating lines if implemented carefully, with added complexity |
| Migration cost | Lower for proof-of-contract on one receipt family | Larger up-front rewrite/test requirement |

## Recommendation

**A — separate, read-only provenance adapter as the first testable experiment**, not as an automatic matcher. It may return an explicit `COMPLETE|PARTIAL|UNAVAILABLE` evidence status; `COMPLETE` is permitted only when system, source hash, physical row number, document family, product, signed quantity, and necessary document-line set are demonstrably consistent. Never promote existing document MATCH to globally confirmed economic ownership solely because document number or summed quantity is equal.

The eventual global ownership rule must remain separate from the adapter: a shared `EventOwnershipLedger` or equivalent verifier prevents two confirmed claims to one physical source row across different matchers. It is not yet proven connected to `investigate_product`.

## Risks and required guards

1. If input rows do not have verified `SourceRowNumber`, do not infer from DataFrame index or pandas enumeration.
2. Source SHA-256 mismatch, missing columns, duplicate document keys, insufficient row granularity or ambiguous split => `UNAVAILABLE` / `REVIEW`.
3. WMS, WME and PRODUCTION require separate source/impact semantics; existing ledger SourceLine accepts only WMS/WME.
4. Existing `ProductInvestigationResult`, `CaseReport`, DOCX, JSON, daily, Streamlit operator workflow must remain unchanged through test-only characterization.
5. Always preserve mathematical conservation (initial = explained + unexplained), no automatic correction, no invented row identities.
6. Do not generalize GOV-002U's successful source-index checks into global GOV-AT-05/06 acceptance.

## Proposed implementation checkpoint (requires separate approval)
- First, **test-only adapter contract** in a dedicated Draft PR, anchored to synthetic receipt with 2 WMS and 2 WME rows. Characterize exact versus ambiguous sets and SHA invalidation. Do not alter engine.
- Next, independently verify backwards-compatible adapter output; test failed provenance and stale cache.
- Only with an explicit architectural approval: implement minimal additive read-only adapter in CORE; run full CI, DOCX/operator regression, and authorized read-only source UAT.
- Only after that, test real cross-matcher ownership conflicts and decide ledger integration.

## Governance
GOV-002V decision recommendation recorded; no authority to modify production code or merge. GOV-002 OPEN, GOV-AT-05/06 OPEN, V1 NO_GO; Draft PRs #56–59 stay unmerged.
