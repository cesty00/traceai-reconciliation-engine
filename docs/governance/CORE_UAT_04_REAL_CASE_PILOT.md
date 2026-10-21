# CORE-UAT-04 — Real authorized reference-case pilot (read-only)
Date: 2026-10-20
Status: SOURCE-READ VERIFIED / NOT ENGINE E2E / NO RELEASE ACCEPTANCE

## Evidence inventory (not raw source content)
- Reference article: DS099904440; stock snapshot 2026-10-11 20:00.
- Report source independently parsed: WME 9811.10 kg, WMS 9724.75 kg, WMS-WME -86.35 kg; one Depositary row at worksheet row 394.
- Original WMS tracking CSV independently parsed with csv.DictReader. Document 00060 on 2026-10-10 has three rows for the article, signed net -86.35 kg. CSV physical line starts: 351551, 351552, 351553. Source SHA-256 and actual row values checked in controlled analysis only; no raw exports or customers committed.
- Original WME XLSX independently parsed read-only, 250823 worksheet rows. Article name appears in 24 warehouse-specific movement records; last primary warehouse record dated 2026-10-08, with balance 9811.10 kg; no document corresponding to 00060 observed for this article in the 2026-10-11 export.
- Therefore -86.35 kg is DOCUMENTARILY ATTRIBUTABLE to WMS 00060 at this snapshot. Operator's prior inventory-rationale statement is separately human-supplied; does not authorize adjustment or create economic MATCH.

## Limits
- This checkpoint is independent source analysis, NOT invocation of full TraceAI CORE engine or production SourceIndex bridge.
- Does not prove no matching WME operation was posted after the source snapshot, nor cover every alternate article identity or reclassification.
- Does not certify ledger ownership GOV-AT-05/06, release UAT or automatic posting.
- No RAW company records placed in GitHub.

## Next safe step
Run instrumented single-case CORE end-to-end on these exact authorized source files with verified SHA and active configuration, compare generated JSON/DOCX with independent findings; if production/nomenclature prerequisites missing, fail-closed and list requirements. Gate behind separate review. GOV-002 OPEN; V1 NO_GO.
