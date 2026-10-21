# CORE INV-01 — Daily authentication and audit integration gate
Date: 2026-10-21
Status: SECURITY DESIGN REVIEW / DAILY WIRING NOT APPROVED

## Verified on current branch
- CI #1411 SUCCESS, all 4 jobs for prior head 04910654.
- daily.py run manifest has authority booleans human_decision_required=true and automatic_approval_allowed, registry_apply_allowed, wms_mutation_allowed, wme_mutation_allowed=false.
- self_service.py validates those same authority boundaries, but these are authorization *policy flags*, not an authentication or case-level reviewer authorization provider.
- An authentication/session provider was not established in the examined Daily and Self-Service modules. Do not assert the entire repository lacks authentication without broader inventory.
- prototypes/core_uat_03/sqlite_review_audit.py consumes caller-controlled trusted_reviewer_id/authorized; those names do not make the inputs trusted. It is unsuitable for direct UI integration.

## Implementation design gate
- Separate trusted server identity adapter, with case scope, verified role and anti-spoofing checks; absence of identity fails closed.
- Document/evidence verification from immutable source snapshot, and staff-role checks before CONFIRMED.
- Persistent SQLite audit must verify reviewer identity and source revision at the transaction boundary, not accept a boolean provided by UI as proof.
- Use transactional case-version conflict detection; append-only history and externally protected audit/backup policy.
- Explicit documentary status distinct from economic MATCH, and no automatic WMS/WME or registry writes.
- Daily read-only preview may be planned, but no decision submission feature should be connected until these gates are proven.

## Acceptance tests before wiring
1. Missing identity / fabricated reviewer -> rejected.
2. Unauthorized role/case access -> rejected.
3. Missing verified original documents/personnel -> remains pending.
4. Stale source SHA -> reject CONFIRMED.
5. Concurrent reviewer conflict -> one successful append, second conflict.
6. Audit history cannot silently change; privileged DB rewrite remains an external security concern.
7. Economic verdict remains REVIEW and mutation flags remain false after documentary confirmation.

Decision: GO for independent authentication-boundary research and test design; NO_GO for connecting human approval into Daily. GOV-002 / GOV-AT-05/06 OPEN, V1 NO_GO, PR #68 Draft.
