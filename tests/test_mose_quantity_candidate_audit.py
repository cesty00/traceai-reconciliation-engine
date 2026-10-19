from traceai_reconciliation.mose_control.quantity_candidate_audit import screen_invoice_delivery_quantities

def invoice():
    return [{"product_name": "A", "quantity": -10}]

def candidate(kind="DIRECT_DELIVERY_CANDIDATE", partner="PARTNER_CANDIDATE", qty=-10):
    return [{"product_name": "A", "quantity": qty, "candidate_class": kind,
             "partner_screen": partner}]

def test_equal_amounts_do_not_produce_match():
    x = screen_invoice_delivery_quantities(invoice(), candidate())
    assert x["items"][0]["status"] == "CANDIDATE_QUANTITIES_EQUAL_UNVERIFIED"
    assert x["automatic_match_allowed"] is False
    assert x["verdict"] == "REVIEW"

def test_internal_transfer_not_counted_as_customer_delivery():
    x = screen_invoice_delivery_quantities(invoice(), candidate("TRANSFER_MOSE"))
    assert x["items"][0]["status"] == "NO_CUSTOMER_DELIVERY_CANDIDATE_REVIEW"

def test_different_partner_not_counted():
    x = screen_invoice_delivery_quantities(invoice(), candidate(partner="DIFFERENT_OR_UNVERIFIED_PARTNER"))
    assert x["items"][0]["wms_customer_delivery_candidate_total"] == 0

def test_different_amount_only_unverified_difference():
    x = screen_invoice_delivery_quantities(invoice(), candidate(qty=-7))
    assert x["items"][0]["status"] == "CANDIDATE_QUANTITIES_DIFFER_UNVERIFIED"

def test_truncated_screen_does_not_claim_absence():
    x = screen_invoice_delivery_quantities(invoice(), [], candidates_truncated=True)
    assert x["items"][0]["status"] == "SCREEN_TRUNCATED_REVIEW"
