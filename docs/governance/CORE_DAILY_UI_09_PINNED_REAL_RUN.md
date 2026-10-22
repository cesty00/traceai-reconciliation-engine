# CORE-DAILY-UI-09 — Pinned-source real six-file integrated verification
Date: 2026-10-22
Status: CORE + READ MODEL VERIFIED / STREAMLIT BROWSER NOT TESTED

## CI and code identity
- Previous CI #1488 for commit 58fc23c4: SUCCESS, all four jobs.
- Retrieved tested source archive for workflow #1488 and compared Git blob SHA-1 on extracted inventory matcher (e9136e6186a50e514dbc66907d7e603f744e66d6) and candidate adapter (b1c3ae0aec38bc533694aa18ac81b1cfd9ac423d) against fetched GitHub files: exact matches.
- This confirms those two module snapshots, not a byte-level verification of every PR file. Tested-source archive excludes apps/daily_readonly.py, hence GUI not covered.

## Actual source-backed execution
- Ran run_self_service_case using six authorized original exports at snapshot 2026-10-11 20:00, product DS099904440, and then inventory_document_candidates(case.json) + operator_view(daily_operator_result.json).
- All commands were read-only to WMS/WME, storing case artifacts in a local output directory.
- Actual result: initial difference -86.35kg, residual 0.00kg, operator status REVIEW.
- WMS inventory candidate documents:
  - 160520206: 1 event, net +160.40kg.
  - 28082026: 4 events, net +0.41kg.
  - 00060: 3 events, net -86.35kg, leading zeros preserved.
- All candidate source statuses UNVERIFIED, human validation PENDING, no economic MATCH or posting.
- WME PV 1178 is not proven documentarily paired with older WMS events; mathematical cancellation is not sufficient.

## Outstanding gates
- Streamlit visual/browser interaction unavailable locally; no claim of browser acceptance. Current zipped CI source artifact lacks the apps/ Streamlit entrypoint.
- Production case/source SHA and physical-line provenance are not yet bound as verified UI claims.
- Per-case authenticated operator confirmation and append-only audit not connected.
- Global economic event ownership GOV-AT-05/06 remains OPEN.
- Release V1 remains NO_GO; PR #68 and #69 are Draft and unmerged.

## Next
Test the Streamlit screen in a controlled environment and check source evidence/role separation; do not enable approve controls or merge until governance gates.
