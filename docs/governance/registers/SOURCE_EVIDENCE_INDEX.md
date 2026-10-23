# C3 — Source evidence and archive-location index (2026-10-23)
Status: READ-ONLY INVENTORY, not full evidence archival. G0 OPEN / CORE NO_GO. Google Drive document IDs below were confirmed by reading the raw-source folders; no raw source bytes copied into GitHub.
| Key | Purpose | Drive file ID | Source date | SHA-256 from frozen local manifest | Confidence |
|---|---|---|---|---|---|
| SRC-WMS-TRACE-1011 | WMS traceability for G1 pilot | 1vxK4imdNEq0WBKLwjD1zFnIibnBX_U5w | export 2026-10-11 | 98e1a88a438d41ff7dda555d8a77f675fd9b2cf6736a636fc5c75bf13c377ece | Drive location VERIFIED; hash from earlier source audit, not recomputed in C3 |
| SRC-WME-MAG-1011 | WME warehouse card | 1mvnlPMNy5XOOw_aefWBLK33ohYC-eN57 | export 2026-10-11 | 735b4756045ae0c5d22e01beb3d77430e105a939c2cbf8b6f0bf28ac3e041495 | Drive location VERIFIED; hash from earlier source audit, not recomputed in C3 |
| SRC-STOCK-1011 | WMS-WME stock report | 1S2HLIxZB-lngcAWu4MIUQdJ4I43fMORv | 2026-10-11 20:00 | ae0982ad7498b30c1c5f3732a8a4cd223158eb527d0c85237c3295d6c3d2d128 | Drive location VERIFIED; hash from earlier audit |
| SRC-WMS-OPEN-0101 | WMS initial stock | 1oOKXLYp-d1h1iFZht9ev0bIRjVC4iJzs | 2026-01-01 | Not independently SHA-confirmed in C3 | Drive location VERIFIED |

Original restricted source folders: WMS 1m_Itbp8TDwpZiAJ9vTObwdk_RNs4vAYC; WME 1_cgs_-Lc86sHkoStcK3NKSouwlj_ya3h. Filenames and file IDs were observed in folder read-back. Never attach raw business transaction lines to public or development GitHub.

## Case provenance
- CASE-G1-001 / DS099904670: WMS source SRC-WMS-TRACE-1011 rows 81730–81745 and 81896–82649 (non-contiguous, see original extraction); WME SRC-WME-MAG-1011 row 78832, internal article 3034, FE 214401. G1-D2 source filtered JSON exists as conversation attachment; durable Drive evidence destination NOT VERIFIED.
- CASE-G1-002 / 20011: WME SRC-WME-MAG-1011 internal article 1492 source rows 96997–97045 at 2025-12-27–31 and 98827–98842 BC on 2026-10-06; WMS SRC-WMS-OPEN-0101 item 20011 initial 75227 pieces. G1-D5–D10 source extracts and regression plans exist as conversation attachments; durable Drive evidence destination NOT VERIFIED.

## Archive gap inventory
- GitHub summaries: CURRENT_STATUS.md G1-D2–D10, C1 case opening audit, central registers; verified repository files.
- Google Drive metadata searches for names G1-D and G1_D returned no matches. This is NOT proof no files are stored under alternate titles.
- A separate older report for item 20011 exists on Drive as Raport_verificare_detaliata_20011_2026-10-06.docx (ID 1k0yJlC2U5GhzyaN84PnLrCqXSEIbWSAX), NOT automatically equated to the new G1 evidence pack.
- Detailed chat artifacts not yet confirmed archived: raw_DS099904670_target_g1_d2.json; TraceAI_G1_D4_protocol_validare_operator.md; TraceAI_G1_D5_20011_COR_STOC_evidence.json; TraceAI_G1_D6_20011_pair_review.json; TraceAI_G1_D7_20011_code_review.md; TraceAI_G1_D8_20011_CORE_WME_checkpoint.md; TraceAI_G1_D9_20011_checkpoint.md; TraceAI_G1_D9_20011_WME_source_audit.json; TraceAI_G1_D10_20011_coverage_audit.json; TraceAI_G1_D10_COR_STOC_regression_spec.md.
- Next control: choose approved restricted archive folder for case evidence; persist evidence with content SHA/metadata and verify read-back, without source-byte duplication in Git; then reconcile exact case references, decisions and closure statuses. Do not mark ARCHIVED unless verified.
