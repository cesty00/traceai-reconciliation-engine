from traceai_reconciliation.mose_control.direct_dp_delivery_review import assess_mose_direct_dp_invoice

INVOICE=[{"warehouse":"DEPOZIT PRINCIPAL","quantity":-10}]
def candidate(cls, partner, doc):
    return {"candidate_class":cls,"partner_screen":partner,"document":doc}

def test_direct_customer_delivery_stays_unverified():
    x=assess_mose_direct_dp_invoice(INVOICE,[candidate("DIRECT_DELIVERY_CANDIDATE","PARTNER_CANDIDATE","ORDER-1")])
    assert x["status"]=="DIRECT_CUSTOMER_DELIVERY_CANDIDATES_REVIEW"
    assert x["document_link"]=="NOT_VERIFIED"
    assert not x["automatic_match_allowed"]

def test_internal_route_never_counts_as_customer_delivery():
    x=assess_mose_direct_dp_invoice(INVOICE,[candidate("TRANSFER_MOSE","NOT_APPLICABLE_TRANSFER","TRANSFER_MOSE-1")])
    assert x["status"]=="NO_DIRECT_CUSTOMER_DELIVERY_IN_SCREEN_REVIEW"
    assert x["internal_transfer_candidate_rows"]==1
    assert x["posting_error_proven"] is False

def test_other_customer_is_not_direct_candidate():
    x=assess_mose_direct_dp_invoice(INVOICE,[candidate("DIRECT_DELIVERY_CANDIDATE","DIFFERENT_OR_UNVERIFIED_PARTNER","ORDER-2")])
    assert x["direct_candidate_rows"]==0

def test_truncation_blocks_absence_claim():
    x=assess_mose_direct_dp_invoice(INVOICE,[],truncated=True)
    assert x["status"]=="WMS_SCREEN_INCOMPLETE_REVIEW"

def test_mose_warehouse_is_not_direct_dp():
    x=assess_mose_direct_dp_invoice([{"warehouse":"MOSE","quantity":-10}],[])
    assert x["status"]=="NOT_SINGLE_DP_INVOICE"
