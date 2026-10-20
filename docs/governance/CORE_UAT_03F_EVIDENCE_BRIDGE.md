# CORE-UAT-03F — Isolated Source Evidence Bridge
Date: 2026-10-20
Status: SYNTHETIC / NOT CONNECTED TO CORE

- New `prototypes/core_uat_03/source_bridge.py` dispatches explicit WMS CSV or WME XLSX pointers to isolated verifiers and refuses ambiguous or missing document/product identity.
- Five synthetic tests exercise positive WMS/WME provenance, invalid identity and unsupported inputs.
- Source-row verification is NOT mathematical discrepancy causation, MATCH, operator rationale validation, or adjustment authorization.
- No CORE engine, SourceIndex database schema, Daily runtime, or DOCX production changes.
- Open limitations: WMS actual export header aliases, WME workbook relationship mapping, normalized dates/quantities, trustworthy upstream pointer creation, source access permissions, duplicate event ownership, reviewer audit log, real-RAW performance and compatibility. Fail closed until separately verified.
- Follow-up: confirm CI on exact head, audit negative-case coverage and design a real-source read-only index bridge under explicit separate approval. GOV-002 and GOV-AT-05/06 OPEN; V1 NO_GO.
