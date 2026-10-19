from traceai_reconciliation.mose_control.review_queue import build_mose_review_queue


def real_f91655():
    return {"status": "MULTI_WAREHOUSE_SAME_F_EXIT_REVIEW",
            "invoice_document": "91655", "source_rows": [71944, 72103],
            "warehouses": ["DEPOZIT PRINCIPAL", "MOSE"],
            "quantity_by_warehouse": {"DEPOZIT PRINCIPAL": "-10", "MOSE": "-10"}}


def test_real_f91655_is_operator_case_not_auto_match():
    queue = build_mose_review_queue([real_f91655()])
    assert len(queue) == 1
    assert queue[0]["operator_status"] == "AWAITING_DOCUMENT_CHECK"
    assert queue[0]["engine_verdict"] == "REVIEW"
    assert queue[0]["automatic_correction_allowed"] is False


def test_queue_case_id_is_repeatable():
    a = build_mose_review_queue([real_f91655()])
    b = build_mose_review_queue([real_f91655()])
    assert a[0]["case_id"] == b[0]["case_id"]


def test_missing_source_provenance_cannot_be_queued_as_proven():
    assert build_mose_review_queue([{"status": "SUSPECT", "invoice_document": "1"}]) == []


def test_normal_replay_not_an_operational_exception():
    assert build_mose_review_queue([{"status": "ARITHMETIC_REPLAY_REVIEW",
                                      "invoice_document": "1", "source_rows": [1]}]) == []


def test_multi_cases_are_distinct_by_evidence():
    first = real_f91655()
    second = dict(first, source_rows=[500, 501])
    assert len(build_mose_review_queue([first, second])) == 2
