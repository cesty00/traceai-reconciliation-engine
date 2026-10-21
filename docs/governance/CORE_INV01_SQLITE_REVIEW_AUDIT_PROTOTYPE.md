CORE INV-01 SQLite review audit prototype — 2026-10-21

Status: ISOLATED PERSISTENT TEST PROTOTYPE, NOT DAILY INTEGRATION.

SQLiteReviewAudit stores append-only events using a case revision guard under BEGIN IMMEDIATE, a SHA-256 hash chain, and triggers against UPDATE/DELETE. Six synthetic tests cover persistence, authorization-flag guard, conflicting revisions, append-only correction, mutation prevention and tamper detection.

Limitations: trusted_reviewer_id and authorized are caller-supplied; this is NOT actual authenticated authorization. Hash chaining alone does not prevent a privileged full database rewrite. The prototype does not authenticate people, check source SHA/rows or establish evidence scope. A CONFIRMED test event is not formal operator validation. Do not wire to Daily without a trusted session boundary, source checks and explicit review. No automatic economic MATCH or WMS/WME mutations. PR #68 Draft; GOV-002 and GOV-AT-05/06 OPEN, V1 NO_GO.
