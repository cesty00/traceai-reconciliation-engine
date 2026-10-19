from traceai_reconciliation.mose_control.strict_matching import check_direct_delivery_link


def invoice(**changes):
    row = dict(operation_type="F", product_code="SKU", quantity=-10,
               date="2026-10-08", source_row=101)
    row.update(changes)
    return row


def delivery(**changes):
    row = dict(operation_type="Livrare", document="SFA100",
               order="CLIENT-001", product_code="SKU", quantity=-10,
               date="2026-10-08", source_row=202)
    row.update(changes)
    return row


def test_explicit_unique_identical_evidence_is_supported_but_review():
    result = check_direct_delivery_link(invoice(), [delivery()], explicit_wms_document="SFA100")
    assert result["status"] == "DOCUMENT_SUPPORTED_REVIEW"
    assert result["verdict"] == "REVIEW"
    assert result["wms_source_row"] == 202


def test_no_explicit_link_never_matches_by_product_and_quantity():
    assert check_direct_delivery_link(invoice(), [delivery()], explicit_wms_document=None)["status"] == "NO_EXPLICIT_LINK_REVIEW"


def test_duplicate_document_is_ambiguous():
    result = check_direct_delivery_link(invoice(), [delivery(), delivery(source_row=203)],
                                        explicit_wms_document="SFA100")
    assert result["status"] == "LINK_MISSING_OR_AMBIGUOUS_REVIEW"


def test_transfer_not_treated_as_customer_delivery():
    result = check_direct_delivery_link(invoice(), [delivery(order="TRANSFER_MOSE-1")],
                                        explicit_wms_document="SFA100")
    assert result["status"] == "LINK_MISSING_OR_AMBIGUOUS_REVIEW"


def test_different_product_blocks_link():
    assert check_direct_delivery_link(invoice(), [delivery(product_code="OTHER")],
                                      explicit_wms_document="SFA100")["status"] == "PRODUCT_DIFFERENCE_REVIEW"


def test_different_amount_blocks_link():
    assert check_direct_delivery_link(invoice(), [delivery(quantity=-9)],
                                      explicit_wms_document="SFA100")["status"] == "QUANTITY_OR_DIRECTION_DIFFERENCE_REVIEW"


def test_date_difference_requires_review():
    assert check_direct_delivery_link(invoice(), [delivery(date="2026-10-09")],
                                      explicit_wms_document="SFA100")["status"] == "DATE_DIFFERENCE_REVIEW"


def test_missing_source_row_requires_review():
    assert check_direct_delivery_link(invoice(source_row=None), [delivery()],
                                      explicit_wms_document="SFA100")["status"] == "INCOMPLETE_INVOICE_EVIDENCE_REVIEW"
