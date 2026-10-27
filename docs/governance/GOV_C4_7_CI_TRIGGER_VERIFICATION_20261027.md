# GOV-C4.7 — CI trigger investigation (2026-10-27)
Frozen CORE `e8e9009285a8c7874b05967733089968abaa3309`; isolated test fix branch `fix/c4-5-streamlit-apptest-warning-20261023`, commit `5112373cf193a01553132d7705e3d3831b03c701`.

## Source-verified discovery
- `.github/workflows/tests.yml` at frozen CORE explicitly handles `push` to `fix/**` and also `pull_request`.
- Exact-patch `fetch_commit_workflow_runs` returned empty; connector contract says it **filters to pull-request-triggered runs**. Therefore EMPTY DOES NOT PROVE NO PUSH CI RUN. Earlier C4.6 notes stating no runs without that qualification were too broad.
- Connector has job, log, commit run (PR scoped), rerun-old-job methods but **no workflow_dispatch, push-trigger status listing, or branch Actions run enumeration method**. No new commit or PR created merely to trigger CI.
- A local container check found `pytest` installed but **no `streamlit`**; full authenticated private repo checkout / matching Python+UI dependency environment not established. No representative post-fix test executed during C4.7.

## What is known and unknown
- Baseline run `tests` #39777607040 passed 336, skipped 1; baseline UI run `daily-streamlit-ui-check` #39777606995 failed due to accessing `Warning.message`.
- Isolated patch file was previously readback verified and changes a single test accessor to `Warning.value`.
- **Post-patch status: NOT_VERIFIED**, not PASS, FAIL, or proof no run existed.

## Controlled next action (no new PR necessary)
1. GitHub repo → Actions → `tests` → filter branch `fix/c4-5-streamlit-apptest-warning-20261023`; check run head SHA exactly `5112373cf193a01553132d7705e3d3831b03c701`.
2. Actions → `daily-streamlit-ui-check` → same branch and SHA; check if its workflow responds to push on `fix/**` or only PR. If only PR, do not create one before G0 PR disposition approval.
3. For each matching run, record run URL, trigger event, SHA, job conclusions, assertion output and skipped/warnings. If no run existed, approved workflow trigger or controlled test environment required.
4. After *both* suites pass for the same SHA, review integration separately. No merge or core rewrite automatically.

Status C4.7 = TRIGGER_AUDITED / PUSH_RUN_VISIBILITY_LIMITED / POST_PATCH_CI_NOT_VERIFIED / G0 OPEN / CORE NO_GO.
