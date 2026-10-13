# v0.12 Technical Release Sign-off

Status: **TECHNICALLY ACCEPTED — PENDING HUMAN RELEASE APPROVAL**

Candidate version: `0.12.0`  
Validated commit: `e784299eeb3e0063bad7c9ab5321db168f3bcb2b`

## CI evidence

Post-merge workflow `tests #715` completed successfully on `main`.

Required gates:
- `pytest`: SUCCESS
- `daily-release-gate`: SUCCESS
- `release-readiness-gate`: SUCCESS
- `release-candidate-gate`: SUCCESS

## Controlled pilot evidence

Pilot rerun:
- run id: `PILOT-V0.12-2026-10-11-R2`
- engine version: `0.12.0`
- cases checked: 3
- status: `SUCCESS_WITH_REVIEW`
- errors: 0
- pilot validator: `accepted=true`
- pilot blockers: none

The pilot used the tested source artifact produced by workflow #715 and the same real source snapshot dated 11.10.2026.

### Case outcomes

1. `DS099904475`
   - difference: `+61.46`
   - operator status: `REVIEW`
   - cause status: `NEDETERMINATA`
   - residual: `60.34`
   - blocker: `AUTO_EXPLAIN_NOT_EXACT`
   - correct release behavior: no forced MATCH and no automatic correction.

2. `DS099904411`
   - difference: `0.0`
   - history: `ZERO_STABLE`
   - cause status: `CONFIRMATA`
   - no blockers
   - current-run history status is finalized as `SUCCESS_WITH_REVIEW`, not `RUNNING`.

3. `10002`
   - difference: `-872.0`
   - operator status: `REVIEW`
   - cause status: `NEDETERMINATA`
   - residual: `-872.0`
   - blocker: `AUTO_EXPLAIN_NOT_EXACT`
   - correct release behavior: no forced MATCH and no automatic correction.

## Auditability fix verified

The first pilot exposed that the current run could remain represented as `RUNNING` inside operator history artifacts even after the final DAILY result was known.

The fix merged in commit `e784299...` now renders the current run with its final status. The second pilot verified that all three current history entries are `SUCCESS_WITH_REVIEW`.

The pilot validator now also rejects any final pilot artifact where the current run still appears as `RUNNING`.

## Safety boundary verified

The candidate retains the required fail-closed authority contract:
- human decision required;
- automatic approval disabled;
- registry apply disabled;
- WMS mutation disabled;
- WME mutation disabled.

The pilot did not perform WMS/WME mutations.

## Engineering conclusion

From a software engineering and release-readiness perspective, `v0.12.0` has passed:
- regression CI;
- DAILY release gate;
- release-readiness gate;
- release-candidate gate;
- controlled real-data pilot;
- pilot acceptance validation;
- post-pilot auditability regression fix;
- pilot rerun after the fix.

The candidate is therefore **technically eligible for internal release**.

This document does not constitute business/accounting approval. Final promotion to internal stable release requires explicit human approval.
