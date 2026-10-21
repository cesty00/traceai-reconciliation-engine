# CORE INV-01 — WMS document text preservation
Date: 2026-10-21
Status: DRAFT / NO MERGE

CI #1390 on previous head 43c0e38a passed 4/4 jobs. Real pilot showed WMS Document intrare '00060' becoming numeric 60.0 in pandas/SQLite cache. Patch applies dtype={'Document intrare': str} to source_index._csv_chunks and source_readers.filter_csv_by_values. Cache filename versioned operational_sources_v2.sqlite to avoid reusing pre-fix lossy data. Two synthetic tests cover both ingestion paths and versioned cache. Existing economic matching unchanged. Other document columns, cache consumers and end-to-end case must be evaluated prior to acceptance; raw SHA and physical-row pointers still unverified. GOV-002 / GOV-AT-05/06 OPEN, V1 NO_GO.
