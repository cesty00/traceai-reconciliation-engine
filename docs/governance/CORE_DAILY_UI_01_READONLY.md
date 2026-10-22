# CORE-DAILY-UI-01 — Read-only Streamlit preview
Date: 2026-10-21
Status: ISOLATED PREVIEW / NOT DEPLOYED / NO REVIEW ACTIONS

- New apps/daily_readonly.py renders existing daily_operator_result.json using src/traceai_reconciliation/daily_ui/read_model.py.
- Run in a trusted local environment: pip install -e '.[ui]'; streamlit run apps/daily_readonly.py -- --case /path/to/daily_operator_result.json.
- Case file path is an operator/server launch argument, not a generic public upload feature. Do not expose sensitive case JSON on public hosting.
- Read-only information includes product, difference, residual, motor cause/status, rules, evidence, action and blockers.
- The existing operator_status text (including CONFIRMAT) is labeled explicitly as motor status, NOT documented human validation. Documentary validation remains NOT_AVAILABLE.
- No buttons to approve; no audit persistence or source verification; no automatic MATCH, WMS/WME or registry writes.
- Four synthetic model contract tests. The Streamlit GUI itself is not browser-tested and no authenticated deployment is provided.
- Existing CORE calculation, matcher and DOCX untouched. PR Draft, GOV-002/GOV-AT-05/06 OPEN, V1 NO_GO.
