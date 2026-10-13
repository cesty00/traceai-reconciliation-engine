"""Regression based on actual 10002 WMS/WME BC quantities.
The input is an operator-verified real documentary discrepancy; the
investigation must not present it as a confirmed final-stock cause.
"""
from traceai_reconciliation.investigation.auto_explain import auto_explanation_from_investigation
from traceai_reconciliation.investigation.models import ProductInvestigationResult


def test_10002_bc_difference_is_not_automatically_a_stock_cause():
    # WMS production input 0023448_DC: -720; WME BC 23448: -90.
    # Documentary residual -630; actual 10002 stock report difference -872.
    case = ProductInvestigationResult(
        case_id="REAL-10002-BC23448",
        product_code="10002",
        product_name="CUTIE FRESH DIM INTERIOARA 342x342x208MM",
        unit="BUC",
        period="01.01.2026-11.10.2026",
        report_date="11.10.2026",
        initial_difference=-872.0,
        details={
            "production_input_matching": {
                "persistent_residual_total": -630.0,
                "residual_total": -630.0,
                "production_confirmed": True,
                "safe_to_auto_explain": True,
                "applied_to_explanation": True,
            }
        },
    )
    explanation = auto_explanation_from_investigation(case)
    assert "PROD-03" not in explanation.rules
    assert explanation.explained_difference == 0.0
    assert explanation.residual_difference == -872.0


def test_10002_bc_is_not_attributed_on_nonboolean_stock_flag():
    case = ProductInvestigationResult(
        case_id="REAL-10002-BC23448",
        product_code="10002",
        product_name="CUTIE FRESH DIM INTERIOARA 342x342x208MM",
        unit="BUC",
        period="01.01.2026-11.10.2026",
        report_date="11.10.2026",
        initial_difference=-872.0,
        details={
            "production_input_matching": {
                "persistent_residual_total": -630.0,
                "safe_to_auto_explain": True,
                "stock_effect_verified": "true",
            }
        },
    )
    explanation = auto_explanation_from_investigation(case)
    assert "PROD-03" not in explanation.rules
