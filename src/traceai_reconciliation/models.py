from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProductAudit:
    product_code: str
    product_name: str | None = None
    opening_stock_wms: float | None = None
    reported_stock_wms: float | None = None
    reported_stock_wme: float | None = None
    calculated_stock_wms: float | None = None
    calculated_stock_wme: float | None = None
    difference_reported: float | None = None
    verdict: str = "REVIEW"
    evidence_level: str = "D"
    cause: str = "UNKNOWN_REVIEW"
    notes: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
