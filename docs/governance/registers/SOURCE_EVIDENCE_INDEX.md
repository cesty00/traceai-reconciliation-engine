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

## C3.1 — controlled private archive location (2026-10-23)

- Created folder in existing private project: RECONCILIERE WMS-WME / 08_RAPOARTE / G1_DOVEZI_DIAGNOSTIC_2026-10-11.
- Folder ID: 1yRMd3hR_JDliBvO_PpjycnYQ90Qe3aP7 ; parent 17ryLvcJJSgrB-nxKDgPishiRZctUM7Rv. The parent was inspected as not shared, but **new folder permissions must still be read back** before uploading sensitive evidence.
- Connector upload requires an authenticated connector file URI; available attachments exist only as local /mnt/data paths. Do not fabricate a file URI or assert uploaded status. **All 11 items below are LOCAL_VERIFIED / DRIVE_UPLOAD_PENDING.**
- Local file name -> SHA256 (content fingerprint; never substitute for document-level operator validation):
  * raw_DS099904670_target_g1_d2.json -> e8fa9520c469cd54d499c44f29ccc5988f72e0587913aa878fa62a28d9074e15
  * traceai_g1_d3_wme3034_evidence.json -> aae0212666a8248ee5e02ae517526ecdea7fc0a7a90e81a6075128e5b5dd4827
  * TraceAI_G1_D4_protocol_validare_operator.md -> 13cae8cd8a6f543681582af0169cc82ec8ac64180dd42314e823daa0125d8101
  * TraceAI_G1_D5_20011_COR_STOC_evidence.json -> 0cf0389a5161f6c6a8c1a22e9fdbd62eba91ba41913608a5434ddf67dba5a92f
  * TraceAI_G1_D6_20011_pair_review.json -> 48503b6edf80813bd27f20ce21ce42fabc30c10dc20258f3cdb4fa36832af931
  * TraceAI_G1_D7_20011_code_review.md -> 15087afe482c6553dae34d56c67cebb777e86241838b4f76af15f51b5f801db9
  * TraceAI_G1_D8_20011_CORE_WME_checkpoint.md -> acd8f7c15001400b9be93db97a8d29a859b650a7f0d00ce3ec2395feabe3250b
  * TraceAI_G1_D9_20011_WME_source_audit.json -> 247117ed80bc693e5b0862b942bc61a94050e1548a33f5cee4d54fee036a5f25
  * TraceAI_G1_D9_20011_checkpoint.md -> 55d284652383ba3f1068c401d0e26bcb1f976976b776088a589a4e507547fe08
  * TraceAI_G1_D10_20011_coverage_audit.json -> 10671a8d8db4e1e174cea3254d1c01c5bc366c5b70d11169d495a838ebffccc2
  * TraceAI_G1_D10_COR_STOC_regression_spec.md -> 3c4f732a42fa4dba042dbad4081db059ec14d8b23683fef850ce9696b3bac137
- Subsequent closure requires upload using authorized file connector/file URI, Google Drive metadata readback, exact per-file Drive IDs and content hash check where supported. Avoid duplicate archival; never upload WMS/WME raw company exports into Git.

## C3.1 transfer confirmed 2026-10-23
- Drive folder: 1yRMd3hR_JDliBvO_PpjycnYQ90Qe3aP7
- Archive file: 163mJlY2oaZHjltlme-9aCXyJEq6tiWfn; TraceAI_G1_D2_D10_DOVEZI_PACHET_20261023.zip; size 18487 bytes; listing readback confirmed.
- Local ZIP SHA256 ffa6bf467f85051983d3a9e02a115579501e406ac2a9f862285828881669487c; all eleven member hashes checked before transfer. Remote file SHA256 has not been independently verified. Former upload-pending state superseded by UPLOADED, METADATA_VERIFIED, REMOTE_HASH_PENDING.

## C3.2 remote integrity verification — 2026-10-23
- Retrieved exact uploaded Drive file 163mJlY2oaZHjltlme-9aCXyJEq6tiWfn with authenticated Drive download. Recomputed downloaded bytes SHA256 ffa6bf467f85051983d3a9e02a115579501e406ac2a9f862285828881669487c, matching pre-upload local SHA256; ZIP CRC test PASS; all 11 member SHA256 and size checks PASS against MANIFEST.json. Status REMOTE_INTEGRITY_PASS. Earlier REMOTE_HASH_PENDING superseded.
- Note: internal manifest status text TRANSFER_TO_DRIVE_PENDING describes pre-upload creation, not current external archive status; verified C3.2 status here is authoritative.
- Both G1 cases linked to archive in CASE_REGISTER.md; technical archiving is complete, business causes remain unverified.
