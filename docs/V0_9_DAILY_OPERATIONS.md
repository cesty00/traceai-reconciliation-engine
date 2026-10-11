# v0.9 Daily Operations Readiness

v0.9 turns the validated reconciliation engine into a repeatable daily workflow.

## Goal

One controlled command must:

1. validate all required sources before analysis;
2. capture source SHA-256 identities;
3. load the daily case manifest;
4. create a deterministic run manifest and signature;
5. execute the self-service batch with case-level error isolation;
6. write a daily summary;
7. reuse a completed run when the source/rules/engine/case signature is unchanged;
8. fail closed before analysis when source readiness fails.

The workflow never approves cases, never applies registry changes, and never mutates WMS/WME.

## Command

```bash
traceai-reconcile \
  --daily-profile config/daily_sources.yaml \
  --daily-run-id 2026-10-12 \
  --rules-version 0.9-dev \
  --engine-commit-sha <git-sha>
```

Use `--no-reuse-completed` only when a deliberate rerun is required.

## Daily profile

See `config/daily_sources.example.yaml`.

The profile contains:

- six required source paths;
- batch manifest path;
- output directory;
- investigation period;
- optional report date;
- explicit opening-stock policy;
- indexed-cache policy.

Relative paths are resolved from the YAML profile directory.

## Output contract

Each run is stored below:

```
<output_dir>/<run_id>/
  run_manifest.json
  daily_run_summary.json
  cases/
    self_service_batch_summary.json
    <CASE_ID>/
      case.json
      case.docx
      registry_update.json
      review_queue.json
      self_service_summary.json
```

Global run status:

- `SUCCESS`: no case needs review and no errors;
- `SUCCESS_WITH_REVIEW`: at least one case is eligible, tolerance, hold, or error;
- `FAILED_SAFE`: source readiness or another pre/batch orchestration failure prevented a trustworthy run.

## Idempotency

The daily signature includes:

- engine version;
- rules version;
- engine commit SHA;
- complete daily profile;
- case manifest;
- SHA-256 of every source.

Running the same `run_id` with the same signature reuses the existing completed run instead of executing the batch again.

## Release gate still required

This branch is the first v0.9 milestone, not yet v1.0 release readiness. Before release candidate:

- CI must pass;
- Golden Gate must remain green;
- add a scrubbed daily-run smoke test to CI;
- add previous-run delta classification: NEW / CHANGED / UNCHANGED;
- add operational UI;
- validate multiple consecutive real daily runs.


## Daily delta classification

Each successful run stores a lightweight per-case stock snapshot state and compares it with the most recent successful run.

Per case, the classifier emits:

- `NEW`: case did not exist in the previous run;
- `CHANGED`: reported WMS-WME difference changed;
- `UNCHANGED`: reported difference is unchanged.

Execution policy remains conservative:

- `ANALYZE` for NEW/CHANGED;
- `REANALYZE_SOURCE_CHANGED` when the final difference is unchanged but at least one source SHA changed;
- `REUSE_SAFE` only when both the final difference and all source SHA identities are unchanged.

The run writes `daily_delta.json` and includes the same delta payload in `run_manifest.json`. This classification is a prioritisation and reuse control; it is not itself a reconciliation verdict.
