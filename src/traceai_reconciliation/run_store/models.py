from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    started_at: str
    engine_version: str
    rules_version: str
    commit_sha: str
    signature: str | None
    status: str
    snapshot_at: str | None = None
    previous_run_id: str | None = None
    finished_at: str | None = None


@dataclass(frozen=True, slots=True)
class SourceRecord:
    run_id: str
    source_type: str
    file_name: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class CaseRecord:
    run_id: str
    case_id: str
    product_code: str
    current_difference: float | None
    previous_difference: float | None
    difference_delta: float | None
    execution_policy: str | None
    delta_status: str | None = None
    explained_delta: float | None = None
    status: str | None = None
    cause_code: str | None = None
    evidence_level: str | None = None
    residual: float | None = None
    operator_action: str | None = None
    correction_target: str | None = None
