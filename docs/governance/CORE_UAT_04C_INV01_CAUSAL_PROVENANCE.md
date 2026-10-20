# CORE-UAT-04C — INV-01 source-backed causal attribution gate
Date: 2026-10-20
Status: ACCEPTANCE TEST OPEN / no production modification.

## Evidence
- CI #1350 prior head passed all four jobs.
- Actual six-source CORE pilot DS099904440: WMS document 00060 has net -86.35 kg in three WMS source rows. INV-01 matches this effect and case stays REVIEW, but the INV-01 explanation component does not identify those source rows and document explicitly.
- Static code inspection: auto_explain.py components_from_investigation reads inventory_adjustment_matching.system_difference_effect and creates component INV-01 with a generic description; there is no source-document reference in this component.

## Test checkpoint
- tests/test_core_uat_04c_inv01_provenance_acceptance.py has a strict xfail describing the expected future requirement and a passing invariant that component composition does not mutate numeric/verdict fields.
- The xfail is a **known unfulfilled contract**, not a passed release criterion; should become a normal PASS only after an approved design and verified source-backed links.
- Do not make descriptions match by substring alone in the eventual design: require immutable structured event pointers, unique ownership without double-counting, source-SHA checks, and an additive, versioned DOCX/JSON presentation.

## Separate discrepancy
- WME warehouse-scope discrepancy 4.40 kg (Ambalare General Agrocom) remains independent; do not fold it into INV-01 or recalculate the original reported -86.35 kg.

## Next gate
Review event ownership GOV-AT-05/06 and operator/DOCX compatibility with exact source pointers; obtain approval for any actual CORE change. GOV-002 OPEN, V1 NO_GO, PR #67 Draft.
