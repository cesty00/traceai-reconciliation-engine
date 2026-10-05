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
    """Infer only rules for which the investigation contains evidence."""
    details = result.details
    rules: list[str] = []

    zone = details.get("stock_report_zone_matching", {})
    if zone.get("confirmed_report_mapping_rows", 0):
        rules.extend(["GST-02", "GST-03"])

    receipt = details.get("receipt_matching", {})
    if receipt.get("supported_documents", 0):
        rules.extend(["REC-01", "REC-02"])

    delivery = details.get("delivery_matching", {})
    if delivery.get("derived_receipt_documents", 0):
        rules.append("R-DER-001")
    if (
        delivery.get("residual_documents", 0)
        or delivery.get("wme_only_documents", 0)
    ):
        rules.append("DEL-02")

    transfer = details.get("transfer_mose_matching", {})
    if (
        transfer.get("matches", 0)
        or transfer.get("cancelled_orders", 0)
        or transfer.get("residual_wms_transfers", 0)
        or transfer.get("wme_only_nt", 0)
    ):
        rules.append("TR-MOSE-01")

    production = details.get("production_matching", {})
    if (
        production.get("matched_documents", 0)
        or production.get("reversal_pairs", 0)
        or production.get("residual_adjustments", 0)
    ):
        rules.append("PROD-02")

    production_input = details.get("production_input_matching", {})
    if (
        production_input.get("wms_total", 0)
        or production_input.get("wme_bc_total", 0)
        or production_input.get("residual_documents", 0)
    ):
        rules.append("PROD-03")

    special = details.get("special_status_matching", {})
    if (
        special.get("matched_groups", 0)
        or special.get("residual_corrections", 0)
    ):
        rules.append("GST-04")

    correction = details.get("generic_stock_corrections", {})
    if (
        correction.get("residual_corrections", 0)
        and (
            "WMS-ONLY" in result.cause_code.upper()
            or "MULTI" in result.cause_code.upper()
        )
    ):
        rules.append("ADJ-01")

    # WME-01 is evidence-only by design and never auto-explains a difference,
    # so it is deliberately excluded from Regula_aplicata.

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

    # Preserve stable order and remove duplicates.
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
