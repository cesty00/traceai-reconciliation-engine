# TraceAI Reconciliation Engine — Development governance v1
Date: 2026-10-19 | Owner decision: stabilize original WMS-WME reconciliation first.
Status: Proposed operating plan; not evidence of completed acceptance.

## Product boundary
- P0 CORE: WMS↔WME reconciliation, evidence-based stock difference investigation, DOCX, operator review.
- P1 MOSE: isolated specialist controls, never a replacement for CORE.
- P2 EXT: client configuration / synthetic demonstrations; paused until CORE operational acceptance.
- Power Query / Power BI: learning and reporting track, not core blocker.

## Roles (review lenses used at each checkpoint)
Architecture; WMS/WME specialist; Stock Controller; QA; Data/BI; Product Management + Security/IP.
No autonomous background agents implied.

## Gates
G0 Audit: baseline branches/PRs/dependencies, failing CI/history, current source integrity, risk register.
G1 CORE correctness: real authorized evidence for receipt, delivery, return, transfer, BC, NP, adjustments; no forced MATCH.
G2 Investigations: article→line/document evidence→explanation→DOCX; source provenance verified.
G3 MOSE isolated acceptance: WME invoices/users, NT, WMS customer deliveries versus internal transfers.
G4 Pilot: representative real cases, repeatability, performance, regression suite and operator sign-off.
G5 EXT/demo: two synthetic client profiles integrated only after G4; no real data in distributable demo.

Each gate needs: tested commit SHA, CI outcome, executed datasets (non-sensitive references only), observed results, unresolved risks, human approval. A successful CI alone does not close a gate.

## Change protocol
1. One issue/goal, one designated branch and scope. No CORE, MOSE, EXT mixed implementation PRs.
2. Record expected outcome and negative-case tests before coding.
3. Implement read-only by default. No automatic posting, storno, forced match or fiscal conclusions.
4. Run unit+integration+regression tests. If CI fails, fix or revert before further features.
5. Compare against original documents; mark insufficient evidence REVIEW.
6. Document change, exact commit and outcome; request human acceptance at operational checkpoints.
7. Preserve source traceability and confidential information. Public/demo exports must be synthetic.

## Journal format
| Date | ID | Scope | Base/head commit | Evidence / tests | Decision | State |
|---|---|---|---|---|---|---|
| 2026-10-19 | GOV-001 | GOVERNANCE | docs branch | Documentation only | Establish gates and roles | IN PROGRESS |

## Immediate G0 audit checklist
- Compare main and MOSE Draft PR #56: changed paths/commits and shared dependencies.
- Identify and isolate EXT-001..004 changes from the MOSE branch without deleting or merging blindly.
- Check CI history including previously reported failures #1160 / #1161, not just current green.
- Assess files for real customer data, invoices, or credentials in repository/history.
- Inventory CORE test cases and document which have source-backed operator acceptance.
- Present a proposed split and rollback sequence before altering existing code branches.

## Decision log
ADR-001: One product with CORE and isolated optional modules; CORE correctness before extensibility.
ADR-002: Real authorized sources only in restricted validation; demo 100% synthetic.
ADR-003: A non-match without evidence remains REVIEW; no posting or automatic stock edits.
ADR-004: Keep existing PR #56 Draft; do not merge or rewrite until G0 evidence is reviewed.


## Operating execution protocol v1.1 — 2026-10-22 (owner-requested reset)
This section operationalizes G0-G4; it does not override their order or authorize PR merges.

### Non-negotiable constraints
- CORE WMS-WME accuracy is the first priority. Freeze new UI, MOSE and EXT features until the respective approved gate; maintain current read-only Daily UI only for diagnosis.
- Do not open a new PR merely because a test passes or a presentation improvement is available. First inventory and disposition the existing PR backlog.
- Never fabricate dataset sizes, match rates, case counts, row provenance, or pass/fail evidence. Label VERIFIED (linked source + exact SHA), INFERRED, UNKNOWN, and OPERATOR-CONFIRMED separately.
- No forced MATCH, automatic WMS/WME changes, fictional stock openings, assumption that numeric zero residual is document approval, or real confidential sources in GitHub.
- Each working session starts with this plan, CURRENT_STATUS, active gate and PR/CI checks; ends with a dated checkpoint in CURRENT_STATUS including objective, SHA, evidence, result, remaining risk and next authorized action.
- Each professional lens must sign off its own risk observations: Architecture, WMS/WME, Stock Control, QA, Data/BI, Product+Security. Only the human owner authorizes operational sign-off and structural merges.
- Deviate from the plan ONLY on newly demonstrated defects, security/integrity risks or incorrect assumptions. Record the evidence, proposed deviation, impact and owner decision BEFORE any directional change. Emergency safe stop is always allowed.

### G0 — Controlled baseline, backlog and data inventory (NEXT, OPEN)
Required output A: PR register covering ALL currently open PRs (count at inspection, no assumed total), with head/base SHA, mixed modules, dependency order, CI, real-UAT evidence, conflicts, proposed KEEP / SPLIT / DEFER / CLOSE; no closing or merging without owner approval.
Required output B: baseline SHA and source manifest for authorized WMS/WME/production/opening/stock/nomenclature exports; dataset dates, units, warehouse scope, known parser failures and data quality, with SHA-256; do not copy raw data into Git.
Required output C: read-only COMPLETE CENSUS of ALL stock-report difference rows for the agreed snapshot; actual distinct products, difference sign/absolute quantity, value only if justified, product type, warehouse/management scope, source availability. De-duplicate explicitly, separate counts for rows vs products, and mark missing data. No guessed total.
Required output D: coverage matrix for RECEIPT / DELIVERY / RETURN_IN / TRANSFER / BC / NP / INVENTORY-PV / ADJUSTMENT / STOCK OPENING / WAREHOUSE MAPPING: known tested products, proven matches, REVIEW, known false positives, untested branches and provenance.
G0 exit requires owner approval of PR disposition plan, exact CORE candidate baseline, census and coverage gaps. Do not let architectural paperwork expand indefinitely: each investigation must produce or unblock one of A-D.

### G1 — CORE matching accuracy using the entire population and representative audited samples
1. Perform automatic READ-ONLY census/triage of the full snapshot first; do not perform deep manual investigation of one arbitrary SKU as substitute.
2. Partition by operation family and anomaly/risk: quantity mismatch, missing counterpart, date/doc mismatch, returns/netting, transfers, production, inventory, opening balance, location mapping, unknown.
3. From actual population, choose a reproducible stratified first validation cohort (proposed up to 30 distinct products, distributed across available families, with both large-absolute discrepancies and random/non-cherry-picked cases; owner confirms the actual sample size after census). Log selection method, random seed, SKU list and exclusions. Do not claim representativeness or statistical confidence without support.
4. For each SKU compare motor results independently against original source rows and operator evidence. Record true document/quantity/lot/warehouse, predicted status, actual adjudicated result, false MATCH, false unmatched, unexplained residual, root cause, relevant PR/SHA and human validation.
5. Fix only demonstrated root-cause clusters: one isolated minimal change + negative/positive regression + full affected-cohort rerun. Prefer fixes that resolve a repeated cluster across many SKUs rather than UI changes to one case. Do not force matching to hit a target.
6. Expand to further cohorts until all present high-risk families have source-backed examples and the owner-approved error/coverage acceptance thresholds are met. No threshold is asserted as already achieved.
Report every cycle: #population rows / #distinct SKUs / #scanned / #audited / #MATCH verified / #REVIEW / #false MATCH / #wrong causes / #unexplained / cluster backlog, with denominators, baseline SHA and date. If data unavailable report UNKNOWN.
G1 exit: documented per-family source-backed accuracy and coverage, no unresolved known false-MATCH in acceptance cohort, repeatable CORE run, owner sign-off. G1 cannot close on unit-test count or one product.

### G2 — Proof chain and DOCX
For passing G1 cases, verify SKU→source file SHA→physical row or trustworthy coordinate→document/lot/quantity/sign/warehouse→matcher decision→stock-delta arithmetic→cause/evidence→case.json/DOCX/operator output. UNKNOWN pointers stay UNVERIFIED; numeric confirmation does not equal documentary or operator approval. Gate exit requires audited cases from multiple families, not just inventory.

### G3 / G4 / G5
Follow the original gate order: MOSE separately only after CORE baseline; G4 on a representative repeated pilot with actual operator sign-off, throughput/performance and safe failure behavior; EXT only after G4 and synthetic demonstration. Power Query/Power BI remains a parallel learning track and cannot delay CORE.

### Stop / go checks and work discipline
- STOP feature work if source manifest unavailable, PR baseline ambiguous, dataset corrupted, CI failing on candidate SHA, any proven false MATCH, or economic double-counting; investigate and document first.
- Daily working checkpoint: one bounded deliverable, observed evidence, uncovered defect, decision, next verified step. Never say '25 passed' means operational acceptance.
- No invented schedules or statistics. Targets such as the proposed 30-SKU first cohort are PLANNING TARGETS, not observed counts or proof of generalization.
