"""Product-level investigation pipeline for TraceAI Reconciliation Engine."""

from .case_builder import build_case_report
from .engine import investigate_product, investigation_to_dict
from .models import InvestigationSources, ProductInvestigationResult
from .registry_sync import build_registry_update, infer_applied_rules
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

__all__ = [
    "InvestigationSources",
    "ProductInvestigationResult",
    "investigate_product",
    "investigation_to_dict",
    "build_case_report",
    "build_registry_update",
    "infer_applied_rules",
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
]
