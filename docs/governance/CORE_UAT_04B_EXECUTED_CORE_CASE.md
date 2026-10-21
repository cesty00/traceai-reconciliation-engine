# CORE-UAT-04B — Actual CORE self-service run, authorized real source snapshot
Date: 2026-10-20
Status: EXECUTED / PARTIAL ACCEPTANCE; V1 NO_GO

## Execution facts
- Executed unmodified Python source packaged by CI workflow #1344 (tested source artifact) on local six authorized export files: 2026-10-11 20:00 stock report, WMS movements through 2026-10-11, WME stock card through 2026-10-11, 2026-01-01 WMS opening, production to 2026-10-11, nomenclature export 2026-10-05.
- Call: run_self_service_case(product_code=DS099904440, period=01.01.2026-11.10.2026, use_source_index=True, case_id=CORE-UAT-04-DS099904440).
- Generated case.json, case.docx, daily_operator_result.json, self_service_summary.json, registry_update.json and review_queue.json locally. DO NOT commit real source files or case contents.

## Actual motor result
- Original difference -86.35 kg. Explained -86.35; residual 0; auto_explain EXACT, evidence A, rule INV-01.
- Economic verdict REVIEW, review status STAGED, promotion ELIGIBLE_FOR_HUMAN_REVIEW, no automatic WMS/WME/registry mutation authorized.
- WMS document 00060 has three entries in operation_timeline: -131.75, -0.25 and +45.65 kg, net -86.35.
- IMPORTANT: auto_explain component inventory_adjustment_residual gives net -86.35 but does not reference 00060 or all three physical source lines explicitly: source-row linkage of explanation to documents is NOT ACCEPTED.
- Technical finding: WME ending warehouse balances 9815.500 versus ERP report 9811.100, delta -4.400 kg (AMBALARE GENERAL AGROCOM 4.400); distinct warehouse scope issue requiring review.
- Four technical warnings: product not in WMS opening snapshot; zone-level WMS reconstruction awaiting mapping; one WMS receipt outside inbound matcher; WME non-standard movements left as residual evidence. 8 unmatched operations flagged.
- Operator's separate confirmation of physical inventory for WMS 00060 is not automatic accounting adjustment approval. Do not infer new WME changes after snapshot.

## Acceptance
PASS: actual engine ran on six authorized sources; stock delta and inventory net reproduced; DOCX generated; safety boundary preserved.
NOT PASS: automatic source pointer provenance for INV-01, explanation specifically linked to document 00060/source lines, zone/mapping reconciliation and final operating UAT.
NEXT: Fix/extend evidence contract in isolated tests first, do not change CORE without approval. Verify whether 4.400 warehouse-scope delta affects reporting and define targeted real case acceptance assertions. GOV-002 / GOV-AT-05/06 OPEN; V1 NO_GO.
