# CORE-UAT-03H — Index pointer gate
Date: 2026-10-20
Status: isolated synthetic contract; production integration NOT APPROVED.

Existing _source_meta provides file-level SHA/name/size. Existing WMS pandas rows and WME LineNo do not prove original physical coordinates. New isolated pointer contract requires explicit RAW_PHYSICAL_COORDINATE source, exact SHA format, physical row, source path, and document/article field bindings. This checks pointer SHAPE only, not authenticity: actual verification remains the job of source_evidence and wme_xlsx_evidence.

Five synthetic tests cover valid explicit pointer, rejection of SQLite rowid, missing original row, SHA format, and rejection of WME LineNo. No source index or CORE production changes. No merge. Next: verify CI then test pointer + verifier jointly and validate actual index provenance with authorized real-source dataset. GOV-002 / GOV-AT-05/06 OPEN, V1 NO_GO.
