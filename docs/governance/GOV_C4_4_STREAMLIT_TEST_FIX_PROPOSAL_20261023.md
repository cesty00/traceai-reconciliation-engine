# GOV-C4.4 — Streamlit AppTest targeted repair proposal
Date: 2026-10-23
Scope: **proposed test-only change; NO Python code changed or rerun as part of this checkpoint**.
Baseline CORE candidate: e8e9009285a8c7874b05967733089968abaa3309.
UI failed job #119820431537 in GitHub Actions run #39777606995; primary tests run #39777607040 passed 336, skipped 1.

## Reproduction evidence
- tests/test_daily_ui_11_streamlit_apptest.py blob c578aebaaae0827ab63140696ef0a5c0c24123e8, line 49.
- apps/daily_readonly.py blob 185c8c1e5b246dba4b5fb9aea8f00755cba21c8, contains st.warning("Validarea documentară nu este activată...") near line 38.
- GitHub Actions installed Streamlit 1.66.1 (dependency pyproject.toml permits >=1.39,<2).
- Traceback: `AttributeError: message` from AppTest Warning proxy after evaluating `item.message`. Earlier UI test assertions were reached without failure. This is a test element-access API mismatch; no WMS/WME stock computation implicated.

## Minimal proposed change (not applied)
File: tests/test_daily_ui_11_streamlit_apptest.py
Before:
```python
assert any("Validarea documentară" in item.message for item in at.warning)
```
After:
```python
assert any("Validarea documentară" in item.value for item in at.warning)
```
Reason: Streamlit testing Element exposes `value` as primary content. Official docs: https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest and https://github.com/streamlit/docs/blob/main/content/develop/concepts/app-testing/get-started.md.

## Guardrails and test plan
1. Limit PR to this test line initially; no changes to application `apps/daily_readonly.py`, business matching, source data, or stock.
2. Re-run **targeted** `pytest -q tests/test_daily_ui_11_streamlit_apptest.py` under Python 3.11 and Streamlit 1.66.1; capture commit SHA, exit code, actual assertions, logs.
3. Verify warning exists and contains intended documentary validation disclaimer; `assert not at.button` remains; test data remain synthetic.
4. Rerun both GitHub workflows (main `tests` and `daily-streamlit-ui-check`) on the same new commit; report summary and no hidden skips. No automatic product release even if both succeed.
5. If test still fails, investigate unexpected warning hierarchy or Streamlit version behavior instead of weakening assert. No forced MATCH or mutations.
6. Track pandas date-format warnings as independent parsing risk, not a reason to modify this patch.

## Approval state
TEST_PATCH_PROPOSED / NOT_APPLIED. CORE frozen baseline unchanged, G0 OPEN / CORE NO_GO. Reconcile change protocol requires owner approval before modifying source/test code.
