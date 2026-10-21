# CORE INV-01 — Daily operator review architecture gate
Date: 2026-10-21
Status: DESIGN ONLY / NOT CONNECTED TO DAILY

## Verified
CI #1405 for commit fc857760: all 4 jobs SUCCESS.
The current human_document_link.py is a nonpersistent prototype; it returns caller-supplied reviewer and a proposed hash but does not authenticate identity, commit a durable record, verify a prior hash chain or serialize concurrent updates. Treat its output as UNTRUSTED PROPOSAL, not an authoritative approval.

## Required production architecture
1. Authentication boundary: server binds reviewer_id, account role and session from trusted application identity; never accept those from UI form or JSON submitted by the operator.
2. Authorization: only assigned/authorized reviewers may decide, with server-verified permissions for the specific case and source scope. Self-approval constraints, if applicable, are enforced server-side.
3. Source evidence: candidate binds case_id, snapshot SHA, source files, exact physical rows, documents and current revision; stale documents or unknown people roles stay REVIEW.
4. Decision request: operator submits decision CONFIRMED/REJECTED/INSUFFICIENT, explanation, supporting documents, evidence and people-role verification; server adds reviewer and timestamp. Confirmation concerns *documentary link only*.
5. Persistence: single DB transaction checks current revision, writes append-only audit event, and increments revision. Reject stale competing reviewer submissions (optimistic concurrency).
6. Integrity: events include previous event digest and canonical payload digest; verify complete chain on reads. A hash chain alone cannot prevent an admin from rewriting the entire database: backups, access controls and external audit anchoring are necessary for stronger tamper resistance.
7. No update/delete APIs for audit events; never overwrite earlier review decisions. Corrections append a superseding record.
8. Display contract: show last documentary decision with reviewer/time and its supporting evidence, plus full history. Economic verdict remains REVIEW until separate economic reconciliation/ownership gates; WMS/WME and registry mutation flags remain false.
9. Versioned additive operator JSON and DOCX annex. Reject source hash mismatch and source permission loss. Test legacy report compatibility.
10. Data security: minimize staff PII in generated reports, role-based access and data retention, no real source exports committed.

## Dedicated acceptance tests required before application wiring
- Unknown or spoofed reviewer session rejected.
- Unauthorized user or cross-case submission rejected.
- Evidence stale or missing => cannot CONFIRM.
- Concurrent reviewers on same revision => one commit, one conflict.
- Second reviewer cannot erase first record; audit chain validates and tampering detected.
- CONFIRMED documentary link never switches economic verdict or grants WMS/WME/registry writes.
- Missing reviewed-person evidence => pending.
- UI/DOCX clearly differentiate candidate, operator assertion and mathematically verified attribution.
- Real authorized pilot for PV 1178 and WMS 160520206/28082026 remains HUMAN_VALIDATION_PENDING until checked in app.

## Next safe implementation
Prepare independent audited storage adapter and its tests, with injected trusted identity, but do NOT wire to Daily or CORE economic matcher before explicit review and source-backed UAT. PR #68 remains Draft and unmerged. GOV-002/GOV-AT-05/06 OPEN; V1 NO_GO.
