# CORE-UAT-03C — Exact source provenance proof (isolated)
Date: 2026-10-20
Status: SYNTHETIC TEST PROTOTYPE; NO PRODUCTION INTEGRATION

## Scope
- `prototypes/core_uat_03/source_evidence.py` reopens WMS CSV read-only, recomputes SHA-256 over exact raw bytes, locates physical CSV record start line (including multiline quoted fields), and compares exact document/field values.
- Six new synthetic negative and positive tests in `tests/test_core_uat_03c_source_evidence.py`.
- No CORE engine, Daily, source index, DOCX, or registry modification.

## Findings and open risks
- Existing `SQLiteSourceIndex.read_wms_product` selects `SELECT * FROM wms WHERE Cod articol = ?`; this alone does not establish the physical raw CSV row or source hash per returned record. Do not infer row identity from pandas index.
- Exact hash+line+document equality verifies this source pointer only, not mathematical attribution, rule ownership, WME XLSX physical row, or review identity.
- Encoding/delimiter must reflect the actual import profile; no blind assumption in production.
- Source hash mismatch invalidates present source-backed claim but must not erase older audit history.
- Physical-row convention must match existing source provenance contract before any integration.
- Large-file performance, sensitive-data access, duplicate economic ownership and WME provenance remain unverified.

## Next gate
Verify CI for exact branch SHA, test baseline DOCX schemas structurally, then design read-only evidence adapter to real source index under separate approval. GOV-002 / GOV-AT-05/06 OPEN, V1 NO_GO; no merge.
