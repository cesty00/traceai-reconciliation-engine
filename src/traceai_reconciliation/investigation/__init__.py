"""Product-level investigation pipeline for TraceAI Reconciliation Engine."""

from .case_builder import build_case_report
from .engine import investigate_product, investigation_to_dict
from .models import InvestigationSources, ProductInvestigationResult
from .auto_explain import (
    AutoExplanation,
    ExplanationComponent,
    compose_explanation,
    opening_component,
    components_from_investigation,
    auto_explanation_from_investigation,
    auto_explanation_to_dict,
)
from .registry_sync import build_registry_update, infer_applied_rules
from .golden_gate import (
    GoldenExpectation,
    GoldenGateResult,
    compare_auto_explanation,
    summarize_golden_gate,
)
from .batch import (
    BatchCaseResult,
    BatchCaseSpec,
    BatchSummary,
    load_batch_manifest,
    run_batch,
)
from .registry_backlog import (
    load_registry_export,
    manifest_payload,
    select_registry_cases,
    write_manifest,
)
from .registry_apply_plan import (
    build_registry_apply_plan,
    write_registry_apply_plan,
)
from .self_service import (
    SourceReadiness,
    SelfServiceRunResult,
    SelfServiceBatchCaseSpec,
    SelfServiceBatchCaseResult,
    SelfServiceBatchSummary,
    run_self_service_case,
    run_self_service_batch,
    validate_source_readiness,
)
from .human_review_queue import (
    HumanReviewQueueItem,
    REVIEW_QUEUE_COLUMNS,
    apply_human_review_decision,
    build_human_review_queue_item,
    build_review_queue_payload,
    queue_item_to_dict,
    review_queue_values,
    record_manual_evidence_resolution,
)

__all__ = [
    "InvestigationSources",
    "ProductInvestigationResult",
    "AutoExplanation",
    "ExplanationComponent",
    "compose_explanation",
    "opening_component",
    "components_from_investigation",
    "auto_explanation_from_investigation",
    "auto_explanation_to_dict",
    "investigate_product",
    "investigation_to_dict",
    "build_case_report",
    "build_registry_update",
    "infer_applied_rules",
    "GoldenExpectation",
    "GoldenGateResult",
    "compare_auto_explanation",
    "summarize_golden_gate",
    "BatchCaseSpec",
    "BatchCaseResult",
    "BatchSummary",
    "load_batch_manifest",
    "run_batch",
    "load_registry_export",
    "select_registry_cases",
    "manifest_payload",
    "write_manifest",
    "build_registry_apply_plan",
    "write_registry_apply_plan",
    "HumanReviewQueueItem",
    "REVIEW_QUEUE_COLUMNS",
    "apply_human_review_decision",
    "build_human_review_queue_item",
    "build_review_queue_payload",
    "queue_item_to_dict",
    "review_queue_values",
    "record_manual_evidence_resolution",
    "SourceReadiness",
    "SelfServiceRunResult",
    "SelfServiceBatchCaseSpec",
    "SelfServiceBatchCaseResult",
    "SelfServiceBatchSummary",
    "run_self_service_case",
    "run_self_service_batch",
    "validate_source_readiness",
]
