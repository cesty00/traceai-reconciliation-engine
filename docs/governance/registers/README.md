# TraceAI C2 — Central audit registers
Status: CONTROLLED INITIALIZATION (2026-10-23); G0 OPEN, G1 diagnostic read-only, CORE NO_GO.

The following files are the canonical register *indexes*, not replacements for source data or prior audit evidence:
- CASE_REGISTER.md — one record per operational investigation.
- DEFECT_REGISTER.md — reproducible software findings and proposals.
- OPERATIONAL_RULES.md — distinguish accepted rules from hypotheses.
- DECISION_REGISTER.md — recorded approvals, scope, and pending decisions.

Record requirements: stable ID, owner role, exact evidence reference, baseline SHA, observation, confidence / approval, status, next action, related IDs. In source references, GitHub path+SHA and Drive file ID are acceptable; original row coordinates and SHA256 when available. NEVER put personal identities or raw WMS/WME exports in Git. Never call a diagnosis VERIFIED merely because it appears in a prior conversation. No automatic MATCH or corrective posting.

Change discipline: append or amend with traceable commit; do not delete uncertainty. Case closes only with operator documentary confirmation and explicit resolution, defect closes only with approved change+repro test+regression+CI, decision closes only with explicit approval. Sync CURRENT_STATUS.md after substantive register change. Evidence artifacts currently stored only in chat are NOT archived in Drive or Git until verified.

Restart: read development plan, CURRENT_STATUS.md, these registers, then source evidence, branch/CI, and current operator decision. Untracked case = REVIEW.
