# CORE-DAILY-UI-07 — CI fix and authorized six-source regression
Date: 2026-10-21
Status: LOCAL RECONSTRUCTED PR68 PATCH / NOT EXACT-COMMIT BROWSER UAT

## CI
- GitHub Actions #1476 FAILED: 319 passed, 1 failed, 4 warnings. Test incorrectly accessed document-level source_status in intermediate inventory_document_candidates; final operator_view owns that field.
- Assertion fixed in commit 2c71558f; subsequent GitHub Actions #1480 SUCCESS for all four jobs at head c3e04c22.

## Actual six-source reproduction
- Reused all original authorized 2026-10-11 DS099904440 source exports, with an isolated local copy of previous tested CORE code amended with PR68's matcher document reference and WMS string-import changes. **This is not an exact checked-out SHA of PR68.**
- run_self_service_case generated case.json and daily_operator_result.json. Reported difference -86.35kg, explained -86.35kg, residual 0, economic verdict REVIEW and operator status REVIEW; no WMS/WME mutation.
- Extracted WMS residual candidate groups: 160520206: +160.40kg (1 event), 28082026: +0.41kg (4 events), 00060: -86.35kg (3 events). Document 00060 retained leading zeros.
- Independently reproduced PR69-compatible projection of these candidate groups, all UNVERIFIED / human PENDING; candidate grouping alone does not establish economic ownership or documentary matching.
- The WME PV 1178 association with older WMS adjustments remains pending formal evidence/personnel validation, irrespective of arithmetic cancellation.

## Still required
1. Execute and compare exact pinned PR68 and PR69 code/SHAs, including import/version compatibility and automated integration assertions.
2. Test Streamlit visually in a controlled browser, use authorized data in private environment only.
3. Bind trusted source SHA and physical line provenance to each candidate, validate global event ownership GOV-AT-05/06.
4. Keep separate reason confirmation, source verification, economic verdict and operator authentication.
PR68/69 Draft, no merge; GOV-002/GOV-AT-05/06 OPEN, V1 NO_GO.
