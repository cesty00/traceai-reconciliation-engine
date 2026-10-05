from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class InvestigationSources:
    stock_report: Path
    opening_stock_wms: Path
    wms_movements: Path
    wme_ledger: Path
    production: Path
    nomenclature: Path


@dataclass(slots=True)
class ProductInvestigationResult:
    case_id: str
    product_code: str
    product_name: str
    unit: str
    period: str
    report_date: str

    initial_difference: float
    reported_stock_wms: float | None = None
    reported_stock_wme: float | None = None
    opening_stock_wms: float | None = None
    opening_stock_wme: float | None = None
    calculated_stock_wms: float | None = None
    calculated_stock_wme: float | None = None

    verdict: str = "REVIEW"
    evidence_level: str = "D"
    cause_code: str = "CAUSE-UNKNOWN-REVIEW"
    cause_description: str = "Cauza nu este încă determinată pe baza dovezilor disponibile."
    cause_status: str = "NEDETERMINATA"

    explained_difference: float = 0.0
    unexplained_difference: float = 0.0

    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    operation_timeline: list[dict[str, Any]] = field(default_factory=list)
    unmatched_operations: list[dict[str, Any]] = field(default_factory=list)
    conclusion_traceability: list[dict[str, Any]] = field(default_factory=list)
    sources_used: list[dict[str, Any]] = field(default_factory=list)
    source_hashes: dict[str, str] = field(default_factory=dict)
    technical_warnings: list[str] = field(default_factory=list)

    details: dict[str, Any] = field(default_factory=dict)
