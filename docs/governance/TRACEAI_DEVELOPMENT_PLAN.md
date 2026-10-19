# TraceAI Reconciliation Engine — Development governance v1
Date: 2026-10-19 | Owner decision: stabilize original WMS-WME reconciliation first.
Status: Proposed operating plan; not evidence of completed acceptance.

## Product boundary
- P0 CORE: WMS↔WME reconciliation, evidence-based stock difference investigation, DOCX, operator review.
- P1 MOSE: isolated specialist controls, never a replacement for CORE.
- P2 EXT: client configuration / synthetic demonstrations; paused until CORE operational acceptance.
- Power Query / Power BI: learning and reporting track, not core blocker.

## Roles (review lenses used at each checkpoint)
Architecture; WMS/WME specialist; Stock Controller; QA; Data/BI; Product Management + Security/IP.
No autonomous background agents implied.

## Gates
G0 Audit: baseline branches/PRs/dependencies, failing CI/history, current source integrity, risk register.
G1 CORE correctness: real authorized evidence for receipt, delivery, return, transfer, BC, NP, adjustments; no forced MATCH.
G2 Investigations: article→line/document evidence→explanation→DOCX; source provenance verified.
G3 MOSE isolated acceptance: WME invoices/users, NT, WMS customer deliveries versus internal transfers.
G4 Pilot: representative real cases, repeatability, performance, regression suite and operator sign-off.
G5 EXT/demo: two synthetic client profiles integrated only after G4; no real data in distributable demo.

Each gate needs: tested commit SHA, CI outcome, executed datasets (non-sensitive references only), observed results, unresolved risks, human approval. A successful CI alone does not close a gate.

## Change protocol
1. One issue/goal, one designated branch and scope. No CORE, MOSE, EXT mixed implementation PRs.
2. Record expected outcome and negative-case tests before coding.
3. Implement read-only by default. No automatic posting, storno, forced match or fiscal conclusions.
4. Run unit+integration+regression tests. If CI fails, fix or revert before further features.
5. Compare against original documents; mark insufficient evidence REVIEW.
6. Document change, exact commit and outcome; request human acceptance at operational checkpoints.
7. Preserve source traceability and confidential information. Public/demo exports must be synthetic.

## Journal format
| Date | ID | Scope | Base/head commit | Evidence / tests | Decision | State |
|---|---|---|---|---|---|---|
| 2026-10-19 | GOV-001 | GOVERNANCE | docs branch | Documentation only | Establish gates and roles | IN PROGRESS |

## Immediate G0 audit checklist
- Compare main and MOSE Draft PR #56: changed paths/commits and shared dependencies.
- Identify and isolate EXT-001..004 changes from the MOSE branch without deleting or merging blindly.
- Check CI history including previously reported failures #1160 / #1161, not just current green.
- Assess files for real customer data, invoices, or credentials in repository/history.
- Inventory CORE test cases and document which have source-backed operator acceptance.
- Present a proposed split and rollback sequence before altering existing code branches.

## Decision log
ADR-001: One product with CORE and isolated optional modules; CORE correctness before extensibility.
ADR-002: Real authorized sources only in restricted validation; demo 100% synthetic.
ADR-003: A non-match without evidence remains REVIEW; no posting or automatic stock edits.
ADR-004: Keep existing PR #56 Draft; do not merge or rewrite until G0 evidence is reviewed.
