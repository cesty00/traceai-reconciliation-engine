# Changelog

## 0.12.0

### Added
- persistent SQLite Run Store for DAILY runs, source identities and product history;
- explicit `snapshot_at` persistence and reuse;
- Run Store-first previous-run lookup with manifest fallback;
- Delta Movement Window and Delta Root Cause analysis;
- operator history and consolidated `daily_case_summary.json`;
- explicit schema contract for the daily case summary;
- artifact completeness validation before successful reuse;
- dedicated `release-readiness-gate` in CI.

### Changed
- DAILY now uses persistent state as the primary baseline for previous-run comparisons;
- `engine.py` was incrementally decomposed into smaller modules for timeline construction, nomenclature validation, stock balance calculations, source provenance, opening stock policy, source index policy and product identity resolution.

### Safety
- no forced MATCH;
- human decision remains required;
- no automatic approval;
- no automatic registry apply;
- no WMS mutation;
- no WME mutation.

### Compatibility
- package and engine version: `0.12.0`;
- Run Store schema: v3;
- existing JSON schema contracts remain explicit and independently versioned.
