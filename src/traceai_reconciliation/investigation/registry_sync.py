from __future__ import annotations

from typing import Any

from traceai_reconciliation.reports import CaseReport

from .models import ProductInvestigationResult


REGISTRY_COLUMNS = [
    "CASE_ID",
    "Data_deschidere",
    "Perioada_WMS",
    "Cod_produs",
    "Document_WMS",
    "Document_WME",
    "Tip_eveniment",
    "Cantitate_WMS",
    "Cantitate_WME",
    "Diferenta",
    "Verdict",
    "Nivel_proba",
    "Cauza",
    "Regula_aplicata",
    "Status_investigatie",
    "Observatii",
    "Link_dovezi_Drive",
    "Data_inchidere",
]


def infer_applied_rules(
    result: ProductInvestigationResult,
) -> list[str]:
    """
    Return only rules that materially contributed to the case explanation.

    Operational controls can still appear in findings, warnings and the full
    JSON payload, but they are not written to REGISTRU_CAZURI as
    Regula_aplicata unless the engine marked their component with
    applied_to_explanation=True.
    """
    details = result.details
    rules: list[str] = []

    zone = details.get("stock_report_zone_matching", {})
    if zone.get("applied_to_explanation", False):
        rules.extend(["GST-02", "GST-03"])

    delivery = details.get("delivery_matching", {})
    if delivery.get("applied_to_explanation", False):
        rules.append("DEL-02")
        if delivery.get("derived_receipt_documents", 0):
            rules.append("R-DER-001")

    production = details.get("production_matching", {})
    if production.get("applied_to_explanation", False):
        rules.append("PROD-02")

    production_input = details.get("production_input_matching", {})
    if production_input.get("applied_to_explanation", False):
        rules.append("PROD-03")

    special = details.get("special_status_matching", {})
    if special.get("applied_to_explanation", False):
        rules.append("GST-04")

    correction = details.get("generic_stock_corrections", {})
    if correction.get("applied_to_explanation", False):
        rules.append("ADJ-01")

    # OPEN-01 explains the preserved residual opening difference rather than
    # increasing explained_difference. Keep it when the unexplained remainder
    # is exactly the independently reconstructed opening gap.
    if (
        result.opening_stock_wms is not None
        and result.opening_stock_wme is not None
    ):
        opening_difference = round(
            result.opening_stock_wms - result.opening_stock_wme,
            3,
        )
        if (
            abs(opening_difference) > 0.001
            and abs(
                result.unexplained_difference - opening_difference
            ) <= 0.001
        ):
            rules.append("OPEN-01")

    return list(dict.fromkeys(rules))


def _observation_text(
    result: ProductInvestigationResult,
    report: CaseReport,
    rules: list[str],
) -> str:
    parts = [
        (
            f"Engine {report.engine_version or '-'}; "
            f"verdict {report.verdict}; "
            f"explicat {report.explained_difference:.3f} {report.unit}; "
            f"neexplicat {report.unexplained_difference:.3f} {report.unit}."
        )
    ]

    if rules:
        parts.append("Reguli: " + ", ".join(rules) + ".")

    priority_types = {
        "DELIVERY_RETURN_NET_VS_AE",
        "AE_WME_ONLY",
        "TRANSFER_MOSE_VS_NT",
        "NT_MOSE_WME_ONLY",
        "RECEIPT_SUPPLIER_IN_VS_FE",
        "RECEIPT_TRANSFER_CG_VS_NT",
        "PRODUCTION_IN_VS_BC",
        "COR STOC",
    }
    priority_exceptions = [
        item
        for item in result.unmatched_operations
        if item.get("operation_type") in priority_types
    ]
    if priority_exceptions:
        parts.append(
            f"Excepții operaționale prioritare: "
            f"{len(priority_exceptions)}. "
            "Dovezile auxiliare complete rămân în JSON."
        )

    if result.technical_warnings:
        parts.append(
            f"Avertismente tehnice: {len(result.technical_warnings)}."
        )

    return " ".join(parts)


def build_registry_update(
    result: ProductInvestigationResult,
    report: CaseReport,
) -> dict[str, Any]:
    """
    Build a portable upsert payload for CONTROL_RECONCILIERE_WMS_WME.

    This function does not call Google APIs. External automation/connectors can
    apply the deterministic payload while the engine remains portable.
    """
    rules = infer_applied_rules(result)

    values = {
        "CASE_ID": result.case_id,
        "Data_deschidere": None,
        "Perioada_WMS": result.period,
        "Cod_produs": result.product_code,
        "Document_WMS": None,
        "Document_WME": None,
        "Tip_eveniment": "STOCK_DIFFERENCE",
        "Cantitate_WMS": result.reported_stock_wms,
        "Cantitate_WME": result.reported_stock_wme,
        "Diferenta": result.initial_difference,
        "Verdict": result.verdict,
        "Nivel_proba": result.evidence_level,
        "Cauza": result.cause_code,
        "Regula_aplicata": ", ".join(rules) if rules else None,
        "Status_investigatie": report.case_status,
        "Observatii": _observation_text(result, report, rules),
        "Link_dovezi_Drive": None,
        "Data_inchidere": None,
    }

    return {
        "schema_version": "1.0",
        "target": {
            "spreadsheet": "CONTROL_RECONCILIERE_WMS_WME",
            "sheet": "REGISTRU_CAZURI",
        },
        "operation": "UPSERT",
        "lookup": {
            "primary": {
                "CASE_ID": result.case_id,
            },
            "fallback": {
                "Cod_produs": result.product_code,
                "Perioada_WMS": result.period,
                "Tip_eveniment": "STOCK_DIFFERENCE",
            },
        },
        "columns": REGISTRY_COLUMNS,
        "values": values,
        "preserve_if_empty": [
            "Data_deschidere",
            "Document_WMS",
            "Document_WME",
            "Link_dovezi_Drive",
            "Data_inchidere",
        ],
        "execution": {
            "execution_id": report.execution_id,
            "engine_version": report.engine_version,
            "engine_commit_sha": report.engine_commit_sha,
            "rules_version": report.rules_version,
        },
    }
