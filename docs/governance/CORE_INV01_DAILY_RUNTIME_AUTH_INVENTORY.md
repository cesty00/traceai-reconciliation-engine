# CORE INV-01 — Daily runtime and authentication inventory
Date: 2026-10-21
Status: STATIC INVENTORY / NO IN-APP APPROVAL

## Evidence
- CI #1417 on prior head b79ed133 completed SUCCESS, all four jobs.
- pyproject.toml declares console scripts traceai-reconcile and traceai-pilot-acceptance; dependencies list pandas, openpyxl, PyYAML, python-docx, lxml. No web framework or identity provider declared there.
- cli.py exposes --daily-profile and --daily-run-id and other batch/single-case arguments.
- daily.py and self_service.py publish fail-closed authority flags but no authenticated reviewer session.
- Common candidate paths app.py, streamlit_app.py, src/traceai_reconciliation/operator_app.py and src/traceai_reconciliation/investigation/operator_app.py were not found on this branch. This is not proof about other repositories or unenumerated paths.
- Isolated trusted_reviewer_boundary.VerifiedPrincipal is caller-constructible; passing it is not proof of authentication.
- Isolated sqlite_review_audit accepts a caller-provided authorization boolean and reviewer ID. Never connect it directly to a form.

## Decision and next gate
No real authenticated Daily reviewer approval can be enabled from the verified current components. Stop adding auth-like mock prototypes. Identify the intended deployment host (CLI, separate Streamlit/web frontend, intranet or IdP) and actual server-side identity provider, then design a strict adapter:
1. provider-verified principal/session bound server-side,
2. role + per-case permission with no form-supplied reviewer ID,
3. verified snapshot SHA/source evidence and persons involved,
4. transactional append-only audit with revision conflicts and tamper controls,
5. economic REVIEW preserved independently of documentary approval,
6. negative access tests and source-backed operator UAT before merge.

Until provider deployment is identified: AUTH_PROVIDER_NOT_ESTABLISHED, DAILY_VALIDATION_NO_GO. No WMS/WME mutations or forced MATCH; GOV-002/GOV-AT-05/06 OPEN, V1 NO_GO. PR #68 Draft.
