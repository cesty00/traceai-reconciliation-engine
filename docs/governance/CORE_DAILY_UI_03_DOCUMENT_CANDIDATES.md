CORE-DAILY-UI-03 — 2026-10-21
Status: OPTIONAL JSON CANDIDATES / UI READ ONLY.

Added optional document_candidates to presentation adapter; existing daily_operator_result.json works without it. Streamlit renders separate candidate docs and event lot/quantity. All candidates are deliberately marked UNVERIFIED and human validation PENDING even if payload claims verified. This is presentation only: no CORE producer of document_candidates, no source SHA/row verification, no authorization, no economic attribution and no WMS/WME writes. Three synthetic tests cover legacy, adversarial verification claim and malformed candidate. Browser UI not tested. PR #69 Draft; GOV-002 and GOV-AT-05/06 OPEN, V1 NO_GO.
