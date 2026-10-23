# GOV-C4.3 — exact CORE baseline CI audit (2026-10-23)

Baseline commit: e8e9009285a8c7874b05967733089968abaa3309.
Scope: READ-ONLY GitHub Actions run/job/log verification. Did NOT re-run pytest, checkout code, or modify CORE. Observed GitHub CI records are from 2026-10-22 on Python 3.11.17.

## Run results
- tests run #39777607040, completed SUCCESS. Job pytest #119820431677 SUCCESS: **336 passed, 1 skipped, 4 warnings in 3.33s**. Other jobs daily-release-gate #119820734722 SUCCESS; release-readiness-gate #119820896480 SUCCESS; release-candidate-gate #119821082382 SUCCESS. This is an exact-SHA tested build but not proof of operator UAT, real-source accuracy, or release readiness.
- daily-streamlit-ui-check run #39777606995, completed FAILURE. Job streamlit-apptest #119820431537 FAILED: one test failed, tests/test_daily_ui_11_streamlit_apptest.py::test_daily_streamlit_readonly_renders_documents; Python 3.11.17; 1 failed in 1.51s. Earlier test assertions passed until test attempted at.warning item.message.
- Traceback: tests/test_daily_ui_11_streamlit_apptest.py:49 asserted any("Validarea documentară" in item.message for item in at.warning). streamlit.testing.v1.element_tree.Warning lacks attribute 'message'; AttributeError: message; exit code 1. This is a confirmed failure in test API usage / potential Streamlit version contract, not proof that inventory arithmetic or UI message content is wrong. The intended user-visible warning string was not tested successfully.
- Observed four pandas parsing warnings from source_readers.py:196: dates parsed individually with dateutil due to unspecified format. Classification: warning / potential data parsing consistency risk, not observed test failure.

## Risk/defect classification
- DEF-C4-UI-001: confirmed synthetic UI test failure, probable test API attribute mismatch; owner and QA to determine approved minimal fix and supported Streamlit version; do not change product UI blindly. Severity BLOCKS UI CI; not evidence of wrong WMS/WME reconciled quantities.
- CORE main pytest at exact SHA PASS (336/1 skipped), but separate UI workflow FAIL means **CI composite not all green**; continue G0 OPEN / CORE NO_GO.
- No independent in-this-session pytest execution, because available workspace lacks checked-out exact private repository and direct container git clone cannot resolve github.com. GitHub Actions job logs are authoritative evidence for the previous CI runs, not a new local result.
- No current operational full-population census, source-backed acceptance on every operation family or operator UAT established.

## Next controlled action
1. Inspect baseline test and UI code around the warning assertion; identify correct supported Streamlit AppTest attribute, write a minimal proposed test-only patch (not implementation without owner-approved code scope).
2. Add explicit negative UI assertion that documentary warning exists and read-only flags remain false. Run the targeted test and full workflows on exact new commit before acceptance.
3. Treat pandas date format warning as QA risk to evaluate separately.
4. Do not start new G1 family features while UI CI is failing; keep architecture and signed-off gating separate.

Evidence:
- https://github.com/cesty00/traceai-reconciliation-engine/actions/runs/39777607040
- https://github.com/cesty00/traceai-reconciliation-engine/actions/runs/39777606995
No CORE changes, no stock actions, no forced MATCH.