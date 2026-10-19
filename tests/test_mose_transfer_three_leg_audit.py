from traceai_reconciliation.mose_control.transfer_three_leg_audit import screen_complete_mose_transfer

def row(doc, name, qty, number):
    return {"document": doc, "product_name": name, "quantity": qty, "source_row": number}

def test_complete_transfer_equal_never_auto_matches():
    a = [row("TRANSFER_MOSE-202520832", "A", -10, 10),
         row("TRANSFER_MOSE-202520832", "B", -65, 11)]
    b = [row("62513", "A", -10, 20), row("62513", "B", -65, 21)]
    c = [row("62513", "A", 10, 30), row("62513", "B", 65, 31)]
    x = screen_complete_mose_transfer(a, b, c)
    assert x["status"] == "TRANSFER_QUANTITIES_EQUAL_UNVERIFIED"
    assert x["article_count"] == 2 and x["wms_total"] == 75
    assert x["document_identity"] == "NOT_VERIFIED"
    assert x["automatic_match_allowed"] is False

def test_missing_product_detected():
    a = [row("TRANSFER_MOSE-X", "A", -10, 1)]
    b = [row("125", "A", -10, 2)]
    c = [row("125", "B", 10, 3)]
    assert screen_complete_mose_transfer(a, b, c)["status"] == "TRANSFER_QUANTITIES_DIFFER_REVIEW"

def test_truncated_candidate_screen_cannot_pass():
    a = [row("TRANSFER_MOSE-X", "A", -10, 1)]
    b = [row("125", "A", -10, 2)]
    c = [row("125", "A", 10, 3)]
    assert screen_complete_mose_transfer(a, b, c, truncated=True)["status"] == "TRANSFER_SCREEN_TRUNCATED_REVIEW"

def test_missing_leg_blocks():
    assert screen_complete_mose_transfer([], [], [])["status"] == "TRANSFER_LEG_MISSING_REVIEW"
