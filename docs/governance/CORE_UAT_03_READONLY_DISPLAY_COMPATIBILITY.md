# CORE-UAT-03 — Read-only operator display compatibility prototype

Date: 2026-10-20
Status: ISOLATED PROTOTYPE / NOT APPROVED FOR PRODUCTION
Branch: `docs/core-uat-03-readonly-prototype`
Baseline: `docs/traceai-governance-plan-20261019`

## Scope
- `prototypes/core_uat_03/operator_display.py` is a standalone, no-I/O function.
- `tests/test_core_uat_03_display_prototype.py` contains strictly synthetic tests.
- No imports or calls added to CORE engine, Daily runner, existing DOCX generator, WMS, WME or registry.
- All inputs remain unchanged; outputs are display only. Economic difference and residual copied unchanged.
- Existing `operator_status=CONFIRMAT` is **not** evidence of human justification validation.
- Human reason code is not authority to adjust ERP stock or to promote a MATCH.

## Tested / intended assertions
1. Document/physical row/source hash allow attribution candidate; no human validation inferred.
2. Complete explicit operator evidence can mark the rationale `OPERATOR_VALIDATED` in isolated display only.
3. UNKNOWN reason stays `OPERATIONAL_REVIEW`.
4. Missing physical row or supporting operator document fails closed.
5. WMS/WME mutation authorization is refused.

## Compatibility concerns and remaining blockers
- This prototype does NOT bind to existing Daily output or inspect original source export SHA at runtime.
- The display layer trusts its supplied evidence structure: it does not independently verify source line authenticity or reviewer identity.
- Does not write an append-only audit log or detect concurrent reviewer conflicts.
- Does not version or render DOCX; old CaseReport and DOCX remain unchanged.
- No live UI exists in this prototype; it is a serializable presentation adapter, not a Streamlit screen.
- Does not prove GOV-AT-05/06 economic-event ownership or source-backed end-to-end operation.
- This is NOT operator UAT acceptance or release readiness.

## Recommended next checkpoint
CORE-UAT-03B: Test a **standalone synthetic DOCX annex preview** from display outputs, verifying wording separation, and test backward compatibility with existing CaseReport without modifying production generator. Gate any later integration behind human approval and source-backed validation. Keep PR draft and unmerged.
