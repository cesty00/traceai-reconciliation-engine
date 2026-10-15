from traceai_reconciliation.reports.operator_causes_report import _operational_status

def test_unconfirmed_or_quantity_equal_is_review():
    assert _operational_status() == "REVIEW"
    assert _operational_status(proposed_correction={"system":"WMS","document":"X","operation":"Receptie","evidence":"row 1"}) == "REVIEW"

def test_confirmed_cause_is_explained_not_auto_correction():
    assert _operational_status(confirmed_cause=True) == "EXPLICAT"

def test_correction_requires_approval_and_all_evidence():
    item={"system":"WMS","document":"SFA1","operation":"Receptie","evidence":"WMS row 75956"}
    assert _operational_status(operator_approved=True, proposed_correction=item) == "CORECȚIE PROPUSĂ"
    assert _operational_status(operator_approved=True, proposed_correction={"system":"WMS"}) == "REVIEW"
