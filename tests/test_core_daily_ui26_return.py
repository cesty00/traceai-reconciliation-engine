from traceai_reconciliation.daily_ui.read_model import operator_view
from traceai_reconciliation.investigation.daily_operator import (
    DailyOperatorResult, daily_operator_result_to_dict,
)


def _payload():
    record = DailyOperatorResult(
        schema_version=__import__("traceai_reconciliation.version", fromlist=["OPERATOR_OUTPUT_SCHEMA_VERSION"]).OPERATOR_OUTPUT_SCHEMA_VERSION,
        case_id="CASE-TEST", product_code="DS099904440", product_name="MACROU",
        unit="Kilogram", difference=-86.35, cause="Inventar", cause_status="CONFIRMATA",
        evidence_level="A", rules=("INV-01",), correction_target="REVIEW",
        operator_action="Control documentar", operator_status="REVIEW",
        residual=0.0, evidence=("Inventory reconciliation",), blockers=(),
        warnings=(),
    )
    return daily_operator_result_to_dict(record)


def test_legacy_daily_without_receipts_remains_compatible():
    payload = _payload()
    payload.pop("technical_receipts")
    assert operator_view(payload)["technical_receipts"] == []


def test_return_match_reaches_safe_daily_view():
    payload = _payload()
    payload["technical_receipts"] = [{
        "document": "RET_WME113669", "link_document": "113669",
        "quantity": 0.85, "family": "RETURN_IN", "status": "MATCH",
        "evidence_status": "CROSS_MODULE",
    }]
    view = operator_view(payload)
    assert view["technical_receipts"][0]["status"] == "MATCH"
    assert view["technical_receipts"][0]["human_validation"] == "PENDING"
    assert view["operator_status"] == "REVIEW"
    assert view["difference"] == -86.35


def test_invalid_technical_receipt_rejected():
    payload = _payload()
    payload["technical_receipts"] = [{"family": "RETURN_IN", "status": "APPROVED", "quantity": 0.85}]
    import pytest
    with pytest.raises(ValueError):
        operator_view(payload)
