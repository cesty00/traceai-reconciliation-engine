# GOV-002E — Ledger integration and MOSE index coupling
Date: 2026-10-19
Status: STATIC INSPECTION COMPLETE; SYSTEM-WIDE CLAIMS NOT VERIFIED; G0 OPEN.

## Inspected evidence
- CORE branch inspected: feature/mose-control-arch01-isolated SHA 6a9d0a6e002d6d890b9589627ec698a3b04f5760; associated CI #1189 SUCCESS.
- Direct file inspections: investigation/engine.py (1608 lines); investigation/daily.py (773); investigation/self_service.py; investigation/case_builder.py; investigation/economic_event_ledger.py (78); investigation/source_index.py (686); mose_control/mose_source_index.py (48).
- CORE execution entrypoint files inspected have no occurrences of EventOwnershipLedger, EconomicEvent or economic_event_ledger. This DOES NOT establish that no other module uses the ledger; repository-wide search remains needed.
- economic_event_ledger.py implements confirmed row ownership and raises on repeated confirmed source row. Its standalone unit tests pass in the combined branch CI, but integration into the engine is not demonstrated.
- MOSESQLiteSourceIndex directly subclasses CORE SQLiteSourceIndex and imports private CORE _csv_chunks and _fingerprint. It also calls inherited _build_wme, is_current, ensure_index; this is version-sensitive coupling.
- CORE source_index.py defines _fingerprint (~line 24), _csv_chunks (~line 49), SQLiteSourceIndex (~line 112); MOSE imports and uses these symbols. Regression must use original format WMS CSV and WME XLSX to prove row identities and cache consistency.

## Risk decisions
- R-003 HIGH: global economic ownership enforcement NOT DEMONSTRATED; do not assume duplicate accounting impossible. Need end-to-end tests that force two distinct matchers to claim same physical source row, verify blocked double impact.
- R-007 HIGH: MOSE depends on private CORE index details. Before split, define tested public index adapter interface or explicitly pin contractual compatibility.
- A green CI #1189 cannot certify either item operationally.

## GOV-002F recommendation (next)
1. Inspect remaining indirect consumers of EventOwnershipLedger in repository/commit history and identify actual production use, not merely class existence.
2. Trace MOSE SQLiteSourceIndex inherited calls against CORE implementation, including signature/data schema and index provenance.
3. Specify integration tests that cover real multi-operation mixed cases, then cut plan; do not move code yet.
4. Maintain CORE release NO_GO and PR #56 Draft.

No functional files were modified as part of GOV-002E.
