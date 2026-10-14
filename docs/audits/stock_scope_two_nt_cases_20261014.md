# Two real warehouse-transfer investigations — 2026-03-21 and 2026-03-30

Source exports (2026-10-11):
- WMS: Trasabilitate_WMS_2025-12-15_2026-10-11_export_2026-10-11.CSV
- WME: Fisa_magazie_WME_2025-12-27_2026-10-11_export_2026-10-11.XLSX
- Manual: reconciliation v6 2026-07-08 (Google Drive).

## 50005 / WME 1503 — 2026-03-21
WMS movement M8__03C19521, DEPAMBF -> DEPAMB, signed movement quantity 96000 pieces (WMS transfer, not stock receipt).
WME NT 19462: DEPOZIT PRINCIPAL -64000 and -32000; SECTIE PRODUCTIE +32000 and +64000; net 0.
Candidate physical-to-accounting transfer flow; no common document ID. REVIEW; requires cross-event provenance and direction mapping verification.

## DS099904183 / WME 2312 — 2026-03-30
WMS movement M8__42585A40, MASA -> DEP100, quantity 68 kg.
WME NT 20338: SECTIE PRODUCTIE -68; DEPOZIT PRINCIPAL +68; net 0.
WMS additional COR STOC -18 in DEP100 later on 2026-03-30. The COR STOC adjustment is a distinct economic event; do NOT net it into NT20338 or falsely claim the transfer explains -18.
Candidate physical-to-accounting transfer flow, but no shared document identifier: REVIEW.

## Interpretation limits
The examples suggest a possible location-direction relationship, but they do not prove that DEPAMBF/DEPAMB or MASA/DEP100 map globally to the corresponding WME warehouses. Both examples remain candidates; no CANDIDAT mapping is promoted to VALIDAT.

## Required next acceptance
A real matched event chain must be checked for WMS location, WME warehouse, event category and document/partner context. Test competing transfers on same day to detect false matches, and account for warehouse-specific versus aggregate stock scopes.
