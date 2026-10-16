import pytest
from traceai_reconciliation.investigation.operator_status import set_operator_status, list_operator_statuses, latest_operator_statuses

def test_human_decisions_are_append_only_per_warehouse(tmp_path):
    first=set_operator_status(product_code="40024",warehouse="SECTIE PRODUCTIE",status="IN_ANALIZA",operator_user="test",root=tmp_path)
    second=set_operator_status(product_code="40024",warehouse="SECTIE PRODUCTIE",status="CAUZA_CONFIRMATA",operator_user="test",observation="Document controlat",root=tmp_path)
    assert first!=second
    assert len(list_operator_statuses(root=tmp_path))==2
    assert latest_operator_statuses(root=tmp_path)[("40024","SECTIE PRODUCTIE")]["status"]=="CAUZA_CONFIRMATA"
    assert ("40024","DEPOZIT PRINCIPAL") not in latest_operator_statuses(root=tmp_path)

def test_operator_identity_and_closure_evidence_required(tmp_path):
    with pytest.raises(ValueError):
        set_operator_status(product_code="40024",warehouse="SP",status="IN_ANALIZA",operator_user="",root=tmp_path)
    with pytest.raises(ValueError):
        set_operator_status(product_code="40024",warehouse="SP",status="REVERIFICAT_INCHIS",operator_user="tester",root=tmp_path)
    assert list_operator_statuses(root=tmp_path)==[]
