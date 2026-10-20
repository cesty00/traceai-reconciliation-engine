# CORE-UAT-02 — Operator diagnostic and human validation contract
Date: 2026-10-20
Status: DESIGN-ONLY / IMPLEMENTATION NOT APPROVED

## Evidence and acceptance
Draft PR #66 commit 7beaf319, CI #1276 (39451318454) success: 602 passed, 1 xfailed, 4 warnings. All 4 jobs passed.
Operator-confirmed reference: DS099904440, snapshot 2026-10-11, WMS-WME = -86.35 kg; WMS adjustment document 00060, net -86.35 kg, operator identified rationale as physical inventory, WMS-only at export. These references are for restricted operational case documentation only; do not put raw company source data in code or synthetic test fixtures.

## Minimum operator view (proposed, NOT implemented)
1. Selected article, source snapshot time, WMS/WME quantities, unit and signed difference.
2. Candidate discrepancy events with WMS/WME document, physical source line, operation, date, quantity, warehouse/lot when present, source-hash status; never fabricate a line identity.
3. Distinguish discrepancy attribution ('CAUSE_IDENTIFIED' mathematically / 'REVIEW' if unresolved) from justification ('OPERATIONAL_REVIEW' / 'OPERATOR_VALIDATED').
4. Operator validation captures reason code (INVENTORY, OPERATION_ERROR, OTHER, UNKNOWN), free-text comment, supporting document reference, reviewer identity, validation timestamp, and explicit evidence scope; reject unsupported or missing attribution claims. Recording a reason does not approve any accounting/stock adjustment.
5. Case remains read-only by default: no WMS/WME update, no auto MATCH, no automatic economic CONFIRMED, no inventory close-out.
6. Report must label automatic findings separately from operator statements and show unresolved/remaining difference; old report schema must remain readable unless a separate compatibility test approves a versioned additive extension.
7. Source exports may be stale; invalidation is fail-closed. Audit log must be append-only and access controlled.

## Proposed independent acceptance tests
- Unknown reason -> OPERATIONAL_REVIEW, no WME adjustment suggestion as authorized.
- Operator states physical inventory -> OPERATOR_VALIDATED for rationale only; difference accounting unchanged.
- Mathematical mismatch after confirmation -> REVIEW.
- Missing supporting document / conflicting reviewer update -> remain pending evidence or audit conflict (not silently overwrite).
- Source SHA changed -> invalidate source-backed claim; keep preserved prior audit history with stale indication.
- No double economic count across matcher views: remains GOV-AT-05/06 OPEN until real integration verification.

## Recommended next step
Before implementation, inventory existing Daily UI and case report extension points on a new isolated docs/test branch; prepare a non-mutating operator-display prototype. Do not wire statuses into engine.py, main or production application without distinct approval. GOV-002 OPEN; GOV-AT-05/06 OPEN; V1 NO_GO.
