# CORE INV-01 — Individual economic contribution audit (2026-10-21)
Status: REAL-SOURCE CALCULATION VERIFIED / DOCUMENT EQUIVALENCE REVIEW / NO MERGE

## CI
GitHub Actions #1397 completed SUCCESS all four jobs for preceding head `cdab0d0c`.

## Contributions extracted from actual CORE case.json for DS099904440
Snapshot 2026-10-11 20:00, difference WMS-WME -86.35 kg.

| System | Date | Document | Reason/operation | Signed quantity kg | Event detail |
|---|---|---|---|---:|---|
| WMS | 2026-05-16 | 160520206 | INV-PLS | +160.40 | FDT250730-58 |
| WMS | 2026-08-28 | 28082026 | INV-MIN | -0.34 | FDT250730-58 -0.09; FDT250730-56 -0.25 |
| WMS | 2026-08-28 | 28082026 | INV-PLS | +0.75 | FDT250730-72 +0.25; FDT250730-47 +0.50 |
| WMS | 2026-10-10 | 00060 | INV-MIN | -132.00 | FDT250730-64 -131.75; FDT250730-72 -0.25 |
| WMS | 2026-10-10 | 00060 | INV-PLS | +45.65 | FDT250730-58 +45.65 |
| WME | 2026-08-29 | PV 1178 | PV | +160.81 | DEPOZIT PRINCIPAL; original XLSX physical sheet row 111872, stored LineNo 111326 |

### Arithmetic partition
- Earlier WMS inventory residual effect = 160.40 - 0.34 + 0.75 = **+160.81 kg**.
- WME PV 1178 effect = **+160.81 kg**.
- Thus earlier residual contributions cancel **arithmetically**: 160.81 - 160.81 = 0.
- WMS doc 00060 effect = -132.00 + 45.65 = **-86.35 kg**.
- Global INV-01 = WMS residual +74.46 - WME PV residual +160.81 = **-86.35 kg**.

### Critical distinction
- Mathematical cancellation does **not** establish documentary matching. WMS May 16 to WME Aug 29 exceeds the matcher's allowed 1-day window, and neither a business-authorized bridge nor shared inventory physical count has been verified.
- Engine currently retains *all* these events as unmatched. Do NOT force MATCH of WMS May/Aug to WME PV 1178 or exclude them as proven reconciled.
- Operator-confirmed inventory rationale applies only to WMS 00060. No authority for adjustments, and no confirmation that WME post-snapshot remains unchanged.
- WME source row 111872 has LineNo 111326: confirms why stored LineNo is not XLSX physical row.
- Raw WMS hash and 00060 physical CSV lines were verified separately in CORE_INV01_RAW_CSV_PROVENANCE_CHECK.md; runtime pointers still UNVERIFIED.

## Next operator validation
Request documentary purpose of PV 1178 and WMS inventory adjustments 160520206/28082026; clarify whether they are a genuine linked inventory correction or unrelated counts. Even if human confirms a relation, economic event ownership and source provenance must still be tested before formal matching. Keep GO/NO_GO G0, GOV-AT-05/06 OPEN. V1 NO_GO.
