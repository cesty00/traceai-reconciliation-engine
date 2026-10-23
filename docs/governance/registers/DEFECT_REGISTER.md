# Software defect register — no silent fix
| Defect ID | Component / baseline | Reproduction and impact | Severity / status | Evidence | Exit condition |
|---|---|---|---|---|---|
| DEF-G1-001 | src/traceai_reconciliation/investigation/stock_correction_matching.py at CORE e8e9009285a8c7874b05967733089968abaa3309 | match_generic_wms_stock_corrections filters negative undocumented COR STOC only. Synthetic input negative -14776.1 yields residual -14776.1; balanced (+14776.1, -14776.1) still yields -14776.1; positive alone yields 0. Does not identify candidate opposite-sign pair. **Classification/presentation limitation**, NOT proven final balance error or authorized economic cancellation. | OPEN / diagnostic confirmed / proposed enhancement NOT approved | Code blob fccbc9a7f7872538f7ac8c0b350dd4f38ed96fec; CURRENT_STATUS G1-D2–D8 | Approved isolated test spec; negative false-pair tests, source-backed review, no duplicate ownership, full affected-cohort regression, CI, owner decision |
| RISK-G0-001 | Economic event ownership GOV-AT-05/06 | Cannot globally prove that multiple matches do not reuse a movement. | BLOCKED; risk not a confirmed line-specific bug | TRACEAI_DEVELOPMENT_PLAN.md and CURRENT_STATUS.md | Approved unique ownership semantics, source-backed negative tests |
| RISK-G0-002 | MOSE mixed CORE/EXT branch | Mixed code branches and dependencies; wholesale merge unsafe. | OPEN architecture risk | GOV_002_ARCHITECTURE_AUDIT.md | Approved split, dependency tests and source-backed acceptance |
 
No defect status FIXED or RELEASED, no CORE code changed by C2.
