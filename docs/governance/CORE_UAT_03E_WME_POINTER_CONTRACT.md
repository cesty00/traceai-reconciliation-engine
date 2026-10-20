# CORE-UAT-03E — WME XLSX source pointer proof
Date: 2026-10-20
Status: isolated synthetic prototype; not production integration.

## Implemented
- Read-only verification of the exact XLSX raw-file SHA-256, worksheet XML part, XML physical row coordinate and exact expected cell values.
- Reject missing/ambiguous row, altered source, wrong document, absent worksheet and invalid pointer.
- Six synthetic tests; no company RAW in repo.
- WME LineNo in index is not assumed to match XML row coordinate.
- No CORE engine/index/schema/DOCX modifications.

## Known limits
- No binding to real WME SQLite index or source-hash cache.
- Worksheet is addressed by internal XML path, not sheet display name; mapping via workbook relationships still needs verification.
- Values are lexical XML strings; numeric/date cell canonicalization and formulas are not implemented.
- Verifying provenance does not prove economic impact ownership, justification or MATCH.
- Original XLSX sheet data/row extraction must be validated on controlled authorized sources before UAT acceptance.

## Next
Verify full CI at exact new SHA, then design index-to-source read-only bridge (WMS + WME) with fail-closed source identity. GOV-002 / GOV-AT-05/06 OPEN, V1 NO_GO.
