from __future__ import annotations

from traceai_reconciliation.investigation.case_builder import (
    build_case_report,
)
from traceai_reconciliation.investigation.models import (
    ProductInvestigationResult,
)
from traceai_reconciliation.investigation.registry_sync import (
    build_registry_update,
    infer_applied_rules,
)


def _result(
    unexplained: float,
) -> ProductInvestigationResult:
    result = ProductInvestigationResult(
        case_id="CASE-2026-000006",
        product_code="DS099904127",
        product_name="Produs test",
        unit="BUC",
        period="01.01.2026-04.10.2026",
        report_date="05.10.2026",
        initial_difference=-1419.0,
        reported_stock_wms=0.0,
        reported_stock_wme=1419.0,
        opening_stock_wms=40.0,
        opening_stock_wme=57.0,
        verdict="REVIEW",
        evidence_level="B",
        cause_code="CAUSE-MULTI-PARTIAL",
        cause_description="Cauză parțial explicată.",
        cause_status="PROBABILA",
        explained_difference=-1419.0 - unexplained,
        unexplained_difference=unexplained,
    )
    return result


def test_fully_explained_review_waits_for_human_validation() -> None:
    result = _result(0.0)

    report = build_case_report(
        result,
        engine_version="0.4.0",
        engine_commit_sha="abc123",
        rules_version="0.3",
        execution_id="RUN-TEST",
    )

    assert report.case_status == "ASTEPTARE_VALIDARE"
    assert report.human_intervention_required is True


def test_unresolved_review_remains_in_analysis() -> None:
    result = _result(-17.0)

    report = build_case_report(
        result,
        engine_version="0.4.0",
        execution_id="RUN-TEST",
    )

    assert report.case_status == "IN_ANALIZA"


def test_registry_payload_preserves_external_fields_and_updates_case() -> None:
    result = _result(-17.0)
    result.details = {
        "delivery_matching": {
            "derived_receipt_documents": 11,
            "residual_documents": 2,
            "wme_only_documents": 0,
            "applied_to_explanation": True,
        },
        "transfer_mose_matching": {
            "matches": 4,
            "cancelled_orders": 0,
            "residual_wms_transfers": 1,
            "wme_only_nt": 0,
        },
        "stock_report_zone_matching": {
            "confirmed_report_mapping_rows": 1,
            "applied_to_explanation": True,
        },
    }
    result.unmatched_operations = [
        {"status": "QTY_DIFF"},
    ]

    report = build_case_report(
        result,
        engine_version="0.4.0",
        engine_commit_sha="abc123",
        rules_version="0.3",
        execution_id="RUN-TEST",
    )

    payload = build_registry_update(result, report)

    assert payload["operation"] == "UPSERT"
    assert payload["lookup"]["primary"] == {
        "CASE_ID": "CASE-2026-000006"
    }
    assert payload["values"]["Cod_produs"] == "DS099904127"
    assert payload["values"]["Diferenta"] == -1419.0
    assert payload["values"]["Verdict"] == "REVIEW"
    assert payload["values"]["Nivel_proba"] == "B"
    assert payload["values"]["Status_investigatie"] == "IN_ANALIZA"

    rules = payload["values"]["Regula_aplicata"]
    assert "GST-02" in rules
    assert "GST-03" in rules
    assert "R-DER-001" in rules
    assert "DEL-02" in rules
    assert "TR-MOSE-01" not in rules
    assert "OPEN-01" in rules

    assert "Data_deschidere" in payload["preserve_if_empty"]
    assert "Link_dovezi_Drive" in payload["preserve_if_empty"]
    assert payload["values"]["Data_deschidere"] is None
    assert payload["values"]["Link_dovezi_Drive"] is None


def test_rule_inference_excludes_evidence_only_controls() -> None:
    result = _result(0.0)
    result.opening_stock_wms = 10.0
    result.opening_stock_wme = 10.0
    result.details = {
        "receipt_matching": {
            "supported_documents": 29,
        },
        "production_input_matching": {
            "wms_total": -100.0,
            "wme_bc_total": -100.0,
            "residual_documents": 0,
        },
        "transfer_mose_matching": {
            "matches": 10,
            "residual_wms_transfers": 0,
        },
        "production_matching": {
            "residual_adjustments": 2,
            "applied_to_explanation": False,
        },
    }

    rules = infer_applied_rules(result)

    assert rules == []


def test_rule_inference_uses_applied_component_flags() -> None:
    result = _result(0.0)
    result.opening_stock_wms = 10.0
    result.opening_stock_wme = 10.0
    result.details = {
        "stock_report_zone_matching": {
            "applied_to_explanation": True,
        },
        "delivery_matching": {
            "applied_to_explanation": True,
            "derived_receipt_documents": 4,
        },
        "production_matching": {
            "applied_to_explanation": True,
        },
        "production_input_matching": {
            "applied_to_explanation": True,
        },
        "generic_stock_corrections": {
            "applied_to_explanation": True,
        },
        "special_status_matching": {
            "applied_to_explanation": True,
        },
    }

    rules = infer_applied_rules(result)

    assert rules == [
        "GST-02",
        "GST-03",
        "DEL-02",
        "R-DER-001",
        "PROD-02",
        "PROD-03",
        "GST-04",
        "ADJ-01",
    ]
