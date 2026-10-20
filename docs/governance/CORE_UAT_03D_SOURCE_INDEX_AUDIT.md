# CORE-UAT-03D — Source Index provenance compatibility audit
Date: 2026-10-20
Status: STATIC AUDIT / INTEGRATION NOT APPROVED

## Direct code observations (branch docs/core-uat-03-readonly-prototype)
- `source_index.py::_fingerprint` computes file name, size and SHA-256; `is_current` compares all source metadata and `ensure_index` rebuilds the index when mismatch occurs. This establishes file-level cache validity, not per-record provenance.
- `_csv_chunks` reads WMS CSV using pandas `read_csv` and iterates chunks, which do not preserve physical CSV start-line identifiers in stored SQLite rows. Chunk boundaries, quoted multiline fields and filtered/reordered rows forbid interpreting the DataFrame index or SQLite rowid as the source physical line.
- `read_wms_product` performs `SELECT * FROM wms WHERE TRIM(CAST("Cod articol" AS TEXT)) = ?`; neither original physical row nor per-row SHA is returned.
- WME XLSX `_build_wme` iterates worksheet XML row elements and stores `values.get("A")` in `LineNo`, i.e. a value from column A, **not necessarily the worksheet XML row coordinate** `row_element.get("r")`. Do not equate them.
- Current WME table has columns `LineNo, OperationType, Document, Date, ...`; no explicit XML `r` coordinate. Repeated document numbers and skipped empty/filtered rows make index ordinal unsuitable as physical evidence.

## Acceptance contract for a later integration
1. The physical WMS pointer must contain authoritative raw-source SHA, exact encoding and delimiter, record start-line convention, document, article, date and quantities; verify against original bytes without inference from index rowid.
2. WME pointer must identify exact XLSX file hash, worksheet identity and XML row coordinate (e.g. `<row r="...">`), plus document/product/operation/quantity; never substitute WME `LineNo` without proving its meaning.
3. For both systems return REVIEW if source hash changes, duplicate/ambiguous source record, mismatching field, missing worksheet/row, parser ambiguity or field normalization mismatch.
4. An exact source row proves **provenance only**. It does not prove causation, inventory justification, economic MATCH or accounting authorization.
5. Keep original source RAW immutable. Do not store confidential source data or operator identifiers in GitHub fixtures.
6. Before wiring to Daily, demonstrate cache invalidation, multiline CSV offsets, XLSX missing/skipped rows and report backward compatibility with isolated synthetic tests.
7. Event ownership GOV-AT-05/06 must be independently demonstrated; no double attribution in simultaneous matchers.

## Decision
Design a new read-only provenance adapter and controlled test fixtures only after agreeing on precise raw source pointer contracts. No change to CORE index/database schema or report model at this checkpoint. G0 GOV-002 OPEN, V1 NO_GO.
