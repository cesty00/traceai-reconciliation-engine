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
]
