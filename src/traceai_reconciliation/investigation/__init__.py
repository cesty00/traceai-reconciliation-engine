"""Product-level investigation pipeline for TraceAI Reconciliation Engine."""

from .case_builder import build_case_report
from .engine import investigate_product, investigation_to_dict
from .models import InvestigationSources, ProductInvestigationResult

__all__ = [
    "InvestigationSources",
    "ProductInvestigationResult",
    "investigate_product",
    "investigation_to_dict",
    "build_case_report",
]
