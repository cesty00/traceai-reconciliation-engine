# CORE-UAT-03B — Synthetic DOCX annex and provenance boundary
Date: 2026-10-20
Scope: isolated prototype, no production integration.

## Changes
- `prototypes/core_uat_03/docx_annex.py`: generates **new** DOCX annex, refuses overwrites.
- `tests/test_core_uat_03b_docx_annex.py`: synthetic tests for wording separation, missing row, no overwrite, authority, unchanged CaseReport model.
- Original `reports/docx_report.py`, `report_model.py`, `investigation/engine.py` untouched.

## Provenance caveat
The prototype only checks that source_hash, document_ref and physical_row fields are present. It does **not** compare SHA with actual source exports, verify row content/document linkage, detect duplicated economic attribution, verify operator authentication, or enforce append-only audit. Therefore CAUSE_IDENTIFIED in the prototype is a candidate display status, NOT proof of genuine source-backed identification.

## Risks and next controlled gate
1. Require source-index binding and SHA verification before production use.
2. Refuse unverifiable document/row link and incomplete reviewer audit.
3. Freeze report schema and compare generated legacy DOCX outputs using snapshot/structural tests; current tests only guard original CaseReport fields, not full byte-level backward compatibility.
4. Validate GOV-AT-05/06 event ownership separately.
5. Explicit approval required before connecting to Daily or DOCX production.
