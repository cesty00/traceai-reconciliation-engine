import pytest
from traceai_reconciliation.mose_control.review_import import validate_review_cases


def case():
    return dict(case_id="MOSE-12345", evidence_source_rows=[71944, 72103],
                engine_verdict="REVIEW", automatic_correction_allowed=False)


def test_case_import_accepts_source_backed_review():
    assert validate_review_cases([case()])[0]["case_id"] == "MOSE-12345"


def test_reject_auto_match_claim():
    with pytest.raises(ValueError):
        validate_review_cases([dict(case(), engine_verdict="MATCH")])


def test_reject_unproven_case():
    with pytest.raises(ValueError):
        validate_review_cases([dict(case(), evidence_source_rows=[])])


def test_reject_duplicate_case_id():
    with pytest.raises(ValueError):
        validate_review_cases([case(), case()])
