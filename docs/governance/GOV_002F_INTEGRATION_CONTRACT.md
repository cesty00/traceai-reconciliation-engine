# GOV-002F — Ledger consumers and inherited source-index contract
Date: 2026-10-19 | Status: PARTIAL STATIC AUDIT, NO MIGRATION APPROVAL

## Evidence verified
- Mixed feature branch at 6a9d0a6e; no functional modifications during this task.
- Ledger module declares `SourceLine`, `EconomicEvent`, and `EventOwnershipLedger`; its public API is `register`, `confirmed_impact`, `events`. In prior GOV-002E inspection no references were found in `engine.py`, `daily.py`, `self_service.py`, `case_builder.py`. This is **not** a whole-repository reference search, so global absence cannot be asserted.
- CORE `SQLiteSourceIndex.__init__(cache_dir)` sets index path; `_expected_meta(wms,wme,production)` hashes three sources, `is_current(wms,wme,production)` verifies SourceRowNumber and source meta, `ensure_index(wms,wme,production)` builds atomically, `_build(target,wms,wme,production)` creates tables; `_build_wme(connection,path,batch_size=5000)` streams WME XLSX.
- MOSE subclass `MOSESQLiteSourceIndex` overrides `_expected_meta(...,production=None)` with two-source metadata, overrides `_build(...,production=None)`, uses the inherited `_build_wme`, and delegates `is_mose_current(wms,wme)` to `is_current(wms,wme,wme)` and `ensure_mose_index(wms,wme)` to `ensure_index(wms,wme,wme)`. Passing WME as a placeholder third argument works only as long as overridden implementations ignore production.
- MOSE `_build` imports and uses private CORE helpers `_csv_chunks` and `_fingerprint`; index schema and source-row provenance are shared assumptions, not versioned contracts.

## Risks and critical tests to define BEFORE code splitting
1. **Ledger integration:** construct synthetic mixed-operation case with same source row claimed through two matchers; verify no double economic impact and final difference reconciliation. Then test on authorized original sources with operator review. No result established yet.
2. **MOSE index interoperability:** fixture WMS CSV and WME XLSX, build fresh MOSE index, reuse index without rebuild, edit WME source and require cache invalidation, verify precise SourceRowNumber in both systems, reject wrong/missing columns.
3. **API compatibility:** test subclass inherited methods as called with WME-as-third-arg and modified method signatures; characterize future isolation contract instead of relying on private functions.
4. **Safety:** test no raw source edits and no automatic MATCH on uncertain invoice/transfer candidates.
5. **Release gates:** full original-source E2E, report DOCX verification, security and performance, human acceptance; until then CORE release NO_GO.

## Outcome
Static class/method signature compatibility appears intentional, but no integration execution in this audit. Ledger usage outside inspected files is unverified. Stop further architectural expansion. Next GOV-002G: obtain repository-wide reference evidence (including tests and runtime entrypoints), inspect MOSE index tests for inherited method behavior, and create explicit acceptance test spec before any code changes.

Do not merge, cherry-pick or rewrite PR #56.
