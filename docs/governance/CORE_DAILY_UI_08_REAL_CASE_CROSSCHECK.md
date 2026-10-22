# CORE-DAILY-UI-08 — Real case contract cross-check
Date: 2026-10-21
Status: VERIFIED LOCAL CASE CONTRACT / EXACT-SHA INTEGRATION OPEN

## CI
GitHub Actions #1484 for preceding PR69 head 499dfb93 completed SUCCESS, all four jobs.

## Local authorized case
The saved six-source DS099904440 result in the controlled local workspace contains 8 WMS residual inventory event references in nested case.json; paired daily_operator_result.json has the same case_id, -86.35kg difference, 0kg residual, economic REVIEW and no WMS/WME mutation permission.
- WMS 160520206: 1 event, +160.40kg.
- WMS 28082026: 4 events, +0.41kg.
- WMS 00060: 3 events, -86.35kg.
Projected UI candidate grouping preserves all three documents independently, including leading zeros in 00060.

## Provenance and scope limitations
The local CORE inventory matcher file blob SHA-1 was 18c5d6c0..., while exact PR68 matcher Git blob is e9136e61..., so do NOT claim exact SHA runtime execution. Local test exercised actual saved case JSON and compatible projection arithmetic only. Original raw company files were not committed.
No browser Streamlit test (Streamlit not installed locally), no evidence SHA/physical-row verification inside UI, no global one-event-one-owner confirmation, no human documentary approval. The PV 1178 historical association still awaits formal operator review.
Need pinned-source exact PR68+PR69 test in controlled environment and browser UAT before accepting integrated release. PR68/69 remain Draft, GOV-002/GOV-AT-05/06 OPEN, V1 NO_GO.
