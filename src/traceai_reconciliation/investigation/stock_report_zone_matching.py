from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


REPORT_TO_WME_WAREHOUSE = {
    "DEPOZITARE": "DEPOZIT PRINCIPAL",
    "SECTIE PRODUCTIE": "SECTIE PRODUCTIE",
    "DETERIORATE": "DETERIORATE",
    "MOSTRE": "MOSTRE",
    "PROTAN": "PROTAN",
    "PESTE PROASPAT": "DEPOZIT PESTE PROASPAT",
}

ERP_ZERO_REVIEW_WAREHOUSES = {
    "DETERIORATE",
    "MOSTRE",
    "PROTAN",
}


@dataclass(slots=True)
class StockReportZoneMatchResult:
    rows: list[dict[str, Any]]
    mapping_effect_total: float
    confirmed_report_mapping_rows: list[dict[str, Any]]
    unresolved_rows: list[dict[str, Any]]


def reconcile_stock_report_zones(
    stock_rows: pd.DataFrame,
    wme_final_balances: dict[str, float],
    tolerance: float = 0.001,
) -> StockReportZoneMatchResult:
    """
    Reconcile each stock-report row with the mapped WME warehouse.

    The report's QuantityDifference is WMS - ERP. For mapped warehouses we
    independently compute WMS - WME. Their difference is the report-mapping
    effect.

    For DETERIORATE/MOSTRE/PROTAN, QuantityERP=0 is treated as a report mapping
    artifact only when WMS and WME balances are equal within tolerance.
    """
    required = {
        "Gestiune",
        "QuantityERP",
        "QuantityWMS",
        "QuantityDifference",
    }
    missing = required - set(stock_rows.columns)
    if missing:
        return StockReportZoneMatchResult([], 0.0, [], [])

    normalized_wme = {
        str(warehouse).strip().upper(): float(quantity)
        for warehouse, quantity in wme_final_balances.items()
    }

    rows: list[dict[str, Any]] = []
    confirmed: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    mapping_effect_total = 0.0

    for _, row in stock_rows.iterrows():
        report_warehouse = str(row["Gestiune"]).strip()
        report_key = report_warehouse.upper()
        mapped_wme_warehouse = REPORT_TO_WME_WAREHOUSE.get(report_key)

        erp = float(pd.to_numeric(pd.Series([row["QuantityERP"]]), errors="coerce").fillna(0.0).iloc[0])
        wms = float(pd.to_numeric(pd.Series([row["QuantityWMS"]]), errors="coerce").fillna(0.0).iloc[0])
        report_difference = float(
            pd.to_numeric(
                pd.Series([row["QuantityDifference"]]),
                errors="coerce",
            ).fillna(wms - erp).iloc[0]
        )

        if mapped_wme_warehouse is None:
            item = {
                "report_warehouse": report_warehouse,
                "mapped_wme_warehouse": None,
                "quantity_erp": erp,
                "quantity_wms": wms,
                "wme_balance": None,
                "report_difference": report_difference,
                "actual_system_difference": None,
                "report_mapping_effect": None,
                "status": "UNMAPPED_REVIEW",
            }
            rows.append(item)
            unresolved.append(item)
            continue

        wme_balance = normalized_wme.get(mapped_wme_warehouse)
        if wme_balance is None:
            item = {
                "report_warehouse": report_warehouse,
                "mapped_wme_warehouse": mapped_wme_warehouse,
                "quantity_erp": erp,
                "quantity_wms": wms,
                "wme_balance": None,
                "report_difference": report_difference,
                "actual_system_difference": None,
                "report_mapping_effect": None,
                "status": "WME_BALANCE_MISSING_REVIEW",
            }
            rows.append(item)
            unresolved.append(item)
            continue

        actual_system_difference = wms - wme_balance
        mapping_effect = report_difference - actual_system_difference

        status = "MAPPED"
        if (
            report_key in ERP_ZERO_REVIEW_WAREHOUSES
            and abs(erp) <= tolerance
            and abs(actual_system_difference) <= tolerance
            and abs(report_difference) > tolerance
        ):
            status = "REPORT_ERP_ZERO_MAPPING_CONFIRMED"
        elif abs(mapping_effect) > tolerance:
            status = "REPORT_MAPPING_REVIEW"

        item = {
            "report_warehouse": report_warehouse,
            "mapped_wme_warehouse": mapped_wme_warehouse,
            "quantity_erp": erp,
            "quantity_wms": wms,
            "wme_balance": wme_balance,
            "report_difference": report_difference,
            "actual_system_difference": actual_system_difference,
            "report_mapping_effect": mapping_effect,
            "status": status,
        }
        rows.append(item)

        if status == "REPORT_ERP_ZERO_MAPPING_CONFIRMED":
            confirmed.append(item)
            mapping_effect_total += mapping_effect
        elif status == "REPORT_MAPPING_REVIEW":
            unresolved.append(item)

    return StockReportZoneMatchResult(
        rows=rows,
        mapping_effect_total=float(mapping_effect_total),
        confirmed_report_mapping_rows=confirmed,
        unresolved_rows=unresolved,
    )
