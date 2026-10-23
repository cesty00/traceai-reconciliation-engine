# GOV-C4.1 — Family → CORE function → test → operator evidence matrix
Date: 2026-10-23. STATIC REPO AUDIT, not execution of tests. Baseline CORE candidate `e8e9009285a8c7874b05967733089968abaa3309`; read-only G1, G0 OPEN, CORE NO_GO.

## Evidence levels
- **CODE_PRESENT**: source file and named function were fetched at candidate SHA.
- **TEST_UNVERIFIED**: no candidate-SHA test run, direct candidate branch test inventory or CI result established by C4.1. A GitHub file-search by hypothetical test names returned zero matches on *default branch*; this is not absence proof.
- **SOURCE_REVIEW**: earlier source-level investigation, still requiring human approval.
- **OPERATOR_PENDING**: actual business meaning and economic equivalence not verified.
Never convert CODE_PRESENT or unit-test existence into operationally verified MATCH.

## Matrix

| Family | CORE implementation observed | Rule / test state | Real evidence and outstanding proof |
|---|---|---|---|
| RECEIPT | `receipt_matching.py: match_inbound_receipts`; orchestrated `engine.py: investigate_product` | RULE-001/002; TEST_UNVERIFIED | CASE-G1-001 DS099904670, WMS IN4517/214401 net +6626.700 kg vs WME FE214401 quantity zero. Operator review; receipt vs WMS relocation event ownership pending. |
| DELIVERY | `delivery_matching.py: match_deliveries_and_returns` and `normalize_delivery_document` | RULE-001; TEST_UNVERIFIED | Must audit real customer delivery, 3P and WME AE with warehouse and sign; no new source-backed case accepted in C4.1. |
| RETURN_IN | `delivery_matching.py: match_deliveries_and_returns` (shared path, not necessarily all return forms) | RULE-001; TEST_UNVERIFIED | RET_WME, WME document -1, return against delivery; confirm reversal vs true inbound and residual. |
| TRANSFER | `transfer_mose_matching.py: match_transfer_mose`, `match_transfer_mose_baskets`; `special_status_matching.py: match_special_status_flow` | RULE-002; TEST_UNVERIFIED | MOSE transfer semantics and inter-warehouse economic ownership remain unverified; module presence is NOT acceptance of G3. |
| BC / production inputs | `production_input_matching.py: match_production_inputs`; `production_matching.py: match_production_adjustments` | RULE-001/002; TEST_UNVERIFIED | Verify package units and consumption basis; no independent BC source validation done in C4.1. |
| NP / production outputs | `production_matching.py: match_production_adjustments` | RULE-001; TEST_UNVERIFIED | Exact NP event path and mapping to WMS PRODUCTION-OUT must be traced at row-level before claiming support. |
| INVENTORY / PV | `inventory_adjustment_matching.py: match_inventory_adjustments` | RULE-006; TEST_UNVERIFIED | Operator identifies WMS 00060 dated 2026-10-10 as inventory, ONLY for that document; no global automatic inventory identification proven. |
| ADJUSTMENT / COR STOC | `stock_correction_matching.py: match_generic_wms_stock_corrections`; `inventory_adjustment_matching.py: match_inventory_adjustments` | RULE-003/006; DEF-G1-001 CONFIRMED_CLASSIFICATION_LIMITATION; TEST_UNVERIFIED on candidate in C4.1 | CASE-G1-002 WMS 20011 +/-14776.100 same lot/location; possible numeric offset is NOT verified economic cancellation. Need false-pair negatives and row ownership proof. |
| OPENING STOCK | `opening_stock_policy.py: resolve_opening_stock_wms`; `stock_balance.py: wme_balance_total_at`, `wme_final_balances`, `wms_total_net_movement` | RULE-005; TEST_UNVERIFIED | 20011 WME 2025-12-31 75827 BUC versus WMS 2026-01-01 75227 BUC, -600 conditional on identical scope; three WME StocInitial balance rows not receipts. |
| WAREHOUSE / ZONE MAPPING | `stock_report_zone_matching.py: reconcile_stock_report_zones`, `has_offsetting_zone_differences`; `special_status_matching.py: match_special_status_flow` | RULE-001/002; TEST_UNVERIFIED | Need warehouse-level original evidence, special-status handling, and ownership validation. |
| WME residual unpaired movements | `wme_residual_matching.py: match_wme_residual_movements` | RULE-001; TEST_UNVERIFIED | Need verify that matched rows are not reused and unmatched documents remain REVIEW. |

## Source code verified (frozen candidate)
- engine.py blob `ab5d46c3a2e606f8f7f3b136a4691e2b5af793c6`
- receipt_matching.py blob `d524a75c17898d89ebc2ecdd80f629cee6689ac2`
- delivery_matching.py blob `84ac469ebaa356a8d16255539b20f7b34adf13f7`
- production_matching.py blob `0a404e6e449dd8241eb358e0b84937072d3cbb9b`
- production_input_matching.py blob `ec8c4d976760751466438834d66aaff59e944a8d`
- inventory_adjustment_matching.py blob `5ecdfa46a5655be1bc8075043264e33a21bb44e1`
- transfer_mose_matching.py blob `e11c0f41369e4e0cc0b20dd6f143b47b9b2ac95b`
- stock_correction_matching.py blob `fccbc9a7f7872538f7ac8c0b350dd4f38ed96fec`
- opening_stock_policy.py blob `5d96b4468378d32a2add2fb1841b64beb09c674c`
- stock_balance.py blob `67032e7ba96e131f69dea570355a9e002c23c9d2`
- stock_report_zone_matching.py blob `9338aeca93e98c13fe0cd51c0830ac1abe838c93`
- special_status_matching.py blob `d6358c446f9a5d4315334b3a678c0bb6a5e0671a`
- wme_residual_matching.py blob `c9dee20e69154ffba79e4b8b7faf8977a91a5f02`

## QA acceptance matrix to construct next (G0-D)
For each family above: concrete test path/test case ID at exact candidate SHA; positive control, negative control (wrong qty/doc/lot/unit/warehouse/sign), input source SHA, row IDs, matcher output, false MATCH count and adjudication. Until run or verified branch-level test inventory, label TEST_UNVERIFIED. Prior project tests must be located and inspected, not presumed missing from filename search.

## C4.1 verdict
Function map **recorded** across 11 families. Test mapping **UNVERIFIED**; case-level economic acceptance **OPEN**; no feature implementation or claim of correctness. Next C4.2: identify real tests at candidate SHA using repository tree/test sources, establish controlled baseline run and coverage matrix, then prioritize a single false-MATCH/economic ownership risk. No CORE modification without separate approval.
