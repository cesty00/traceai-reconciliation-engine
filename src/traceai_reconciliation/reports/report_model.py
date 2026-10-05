from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Recommendation:
    priority: str
    action_type: str
    recommendation: str
    proposed_owner: str | None = None
    precondition: str | None = None


@dataclass(slots=True)
class CaseReport:
    case_id: str
    product_code: str
    product_name: str
    period: str
    report_date: str

    initial_difference: float
    explained_difference: float
    unexplained_difference: float
    unit: str

    verdict: str
    evidence_level: str
    cause_code: str
    cause_description: str
    cause_status: str

    executive_summary: str
    sources_used: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    operation_timeline: list[dict[str, Any]] = field(default_factory=list)
    unmatched_operations: list[dict[str, Any]] = field(default_factory=list)
    conclusion_traceability: list[dict[str, Any]] = field(default_factory=list)

    case_status: str = "DESCHIS"
    human_intervention_required: bool = True

    execution_id: str | None = None
    engine_version: str | None = None
    engine_commit_sha: str | None = None
    rules_version: str | None = None
    rules_hash: str | None = None
    source_hashes: dict[str, str] = field(default_factory=dict)
    technical_warnings: list[str] = field(default_factory=list)
