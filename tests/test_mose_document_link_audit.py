from traceai_reconciliation.mose_control.document_link_audit import screen_delivery_document_links

def test_two_customer_orders_are_not_aggregated_to_prove_invoice():
    rows = [{"document": "91655", "product_name": "A", "quantity": -10}]
    candidates = [
        {"document": "ORDER-A", "source_row": 11, "candidate_class": "DIRECT_DELIVERY_CANDIDATE", "partner_screen": "PARTNER_CANDIDATE"},
        {"document": "ORDER-B", "source_row": 12, "candidate_class": "DIRECT_DELIVERY_CANDIDATE", "partner_screen": "PARTNER_CANDIDATE"},
        {"document": "TRANSFER_MOSE-X", "source_row": 13, "candidate_class": "TRANSFER_MOSE", "partner_screen": "NOT_APPLICABLE_TRANSFER"},
    ]
    result = screen_delivery_document_links(rows, candidates)
    assert [x["wms_order"] for x in result["customer_order_candidates"]] == ["ORDER-A", "ORDER-B"]
    assert result["document_link_status"] == "NOT_VERIFIED"
    assert result["automatic_match_allowed"] is False

def test_invoice_without_candidate_keeps_review():
    result = screen_delivery_document_links([{"document": "91655"}], [])
    assert result["customer_order_candidates"] == []
    assert result["verdict"] == "REVIEW"
