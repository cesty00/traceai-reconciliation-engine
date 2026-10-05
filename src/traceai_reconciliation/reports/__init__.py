"""Report generation for TraceAI reconciliation cases."""

from .docx_report import generate_docx_report, validate_case_report
from .report_io import case_report_from_dict, load_case_report_json
from .report_model import CaseReport, Recommendation

__all__ = [
    "CaseReport",
    "Recommendation",
    "case_report_from_dict",
    "load_case_report_json",
    "generate_docx_report",
    "validate_case_report",
]
