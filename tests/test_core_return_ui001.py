from traceai_reconciliation.investigation.receipt_operator_view import classify_receipt_for_operator


def _receipt(qty=0.85, doc="RET_WME113669", link="113669"):
    return [{"document": doc, "quantity": qty, "link_document": link, "status": "REVIEW"}]


def _delivery(wms=0.85, wme=0.85, status="MATCH"):
    return [{"document": "113669", "wms_net_quantity": wms, "wme_ae_quantity": wme, "status": status}]


def test_return_113669_is_technical_match():
    result = classify_receipt_for_operator(_receipt(), _delivery())
    assert result[0]["family"] == "RETURN_IN"
    assert result[0]["status"] == "MATCH"


def test_return_with_quantity_difference_is_not_match():
    result = classify_receipt_for_operator(_receipt(), _delivery(wme=0.8, status="QTY_DIFF"))
    assert result[0]["status"] == "QTY_DIFF"


def test_return_without_counterpart_stays_review():
    result = classify_receipt_for_operator(_receipt(), [])
    assert result[0]["status"] == "REVIEW"


def test_mixed_delivery_and_return_not_promoted():
    result = classify_receipt_for_operator(_receipt(), _delivery(wms=-9.15, wme=-9.15))
    assert result[0]["status"] == "REVIEW"


def test_unknown_receipt_not_promoted_by_same_document():
    result = classify_receipt_for_operator(_receipt(doc="IN_OTHER"), _delivery())
    assert result[0]["family"] == "RECEIPT_UNCLASSIFIED"
    assert result[0]["status"] == "REVIEW"


def test_ambiguous_delivery_document_stays_review():
    result = classify_receipt_for_operator(_receipt(), _delivery() + _delivery())
    assert result[0]["status"] == "REVIEW"
