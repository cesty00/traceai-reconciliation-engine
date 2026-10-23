# TraceAI C4 — Operational rules versus CORE Python: static audit
Date: 2026-10-23. Status: STATIC_CODE_REVIEW_ONLY / NOT TEST EXECUTION. CORE source ref e8e9009285a8c7874b05967733089968abaa3309; G0 OPEN, G1 read-only non-authoritative, CORE NO_GO.

## Scope and method
Read OPERATIONAL_RULES.md (6 recorded rules) and CORE source files at the exact frozen candidate commit: investigation/engine.py (blob ab5d46c3a2e606f8f7f3b136a4691e2b5af793c6), investigation/receipt_matching.py (d524a75c17898d89ebc2ecdd80f629cee6689ac2), investigation/delivery_matching.py (84ac469ebaa356a8d16255539b20f7b34adf13f7), investigation/opening_stock_policy.py (5d96b4468378d32a2add2fb1841b64beb09c674c), investigation/stock_correction_matching.py (fccbc9a7f7872538f7ac8c0b350dd4f38ed96fec), investigation/source_index.py (8cc9d55db23d83344d1277d487989db761a59810).
Existence of a Python module is NOT proof that the business rule is correct in the entire pipeline. No tests or full cohort rerun were executed during C4.

## Rule-by-rule traceability matrix
| Rule | Evidence in code | C4 assessment | Gap and next proof |
|---|---|---|---|
| RULE-001: equality/logical equivalence without forced MATCH | receipt_matching.py match_inbound_receipts and delivery_matching.py match_deliveries_and_returns exist and are imported by engine.py. | PARTIALLY_IMPLEMENTED, GLOBAL_VALIDATION_UNKNOWN | Audit return/transfer/production families, tolerance, units, document normalization, conflicting matches; run full source-backed G1 cohort and false-MATCH negatives. |
| RULE-002: internal WMS transfer is not a second receipt | Dedicated receipt matching and engine orchestration exist. DS099904670 source evidence shows internal moves are physically distinct from receipt. | BUSINESS_RULE_DOCUMENTED; GLOBAL_ECONOMIC_OWNERSHIP_UNVERIFIED | Trace each movement into total/cause arithmetic, demonstrate source-row one-use ownership (GOV-AT-05/06), test internal move no double counting. |
| RULE-003: opposite-sign COR STOC = possible offset, not confirmed cancellation | match_generic_wms_stock_corrections explicitly filters only negative undocumented COR STOC with quantity below 0 and does not detect positive corresponding row. | CONFIRMED_DIAGNOSTIC_LIMITATION / NOT IMPLEMENTED FOR POSSIBLE_OFFSET_REVIEW | Fix proposal not approved; synthetic negative+positive and false-pair tests plus WME document validation needed. Final stock arithmetic bug NOT proven. DEF-G1-001. |
| RULE-004: WME FE 214401 might be unposted after WMS receipt | No cause-specific verified test or explicit automated rule evidenced by reviewed modules; it is user-stated hypothesis only. | HYPOTHESIS, MUST NOT IMPLEMENT AS CONFIRMED_CAUSE | Operator inspect actual FE/NIR and trace alternative documents; keep case AWAITING_OPERATOR. |
| RULE-005: WME StocInitial balance snapshots are not receipts | opening_stock_policy.py resolve_opening_stock_wms handles WMS opening source and explicit missing-opening policy; it does not by itself prove interpretation of three WME StocInitial balance rows. | WMS_OPENING_PATH_EXISTS / WME_INITIAL_SNAPSHOT_SEMANTICS_NOT_PROVEN | Examine WME source reader and calculation separately, verify 20011 Dec31 75827 vs Jan1 WMS 75227 (-600) within same management scope; no arbitrary sum of balances. |
| RULE-006: inventory adjustment classification only with document/operator proof | Stock correction matching selects COR STOC negative by reason, not evidence of inventory. Earlier operator confirmed WMS doc 00060 inventory only; no generic inference justified. | SPECIFIC_OPERATOR_VALIDATION / GENERIC_AUTOMATION_UNVERIFIED | Verify inventory-specific engine logic and document type mappings; isolated examples inventory vs non-inventory, no broad assumption. |

## Risk classification
- DEF-G1-001: confirmed limited classification coverage for positive/negative COR STOC pairs. Not a proven incorrect ending stock calculation.
- GOV-AT-05/06: global event/row ownership unresolved.
- Delivery/return/receipt module presence is a static finding only; cannot claim reliable match rates, all warehouse scopes or pass.
- Missing paths transfer_matching.py and inventory_matching.py at expected guessed names are not evidence that transfer or inventory functionality is absent: look for actual function imports from engine.py before any conclusion.

## Change/release decision
No Python changes, no forced match, no correction in WMS/WME, no CI run and no operator sign-off. Proposed next C4.1: compile source-to-function map for ALL G0-D operation families and select first source-backed positive/negative tests, starting with receipt DS099904670 and adjustment 20011. Only authorize minimal code change after explicit issue/test approval. Business case status remains REVIEW.