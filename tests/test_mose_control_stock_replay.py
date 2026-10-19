from traceai_reconciliation.mose_control.stock_replay import replay_wme_stock

def mv(n, day, warehouse, qty, operation, lot="L1", observed=None):
    return {"source_row": n, "date": day, "warehouse": warehouse, "product_code": "SKU",
            "lot": lot, "quantity": qty, "operation_type": operation,
            "document": str(n), "observed_balance": observed}

OPEN = {("DEPOZIT PRINCIPAL", "SKU", "L1"): 100, ("MOSE", "SKU", "L1"): 0}

def test_two_nt_legs_and_mose_invoice():
    events = [mv(2, "2026-10-02", "MOSE", 100, "NT"),
              mv(3, "2026-10-03", "MOSE", -100, "F"),
              mv(1, "2026-10-02", "DEPOZIT PRINCIPAL", -100, "NT")]
    result = replay_wme_stock(events, opening_balances=OPEN)
    assert {b["warehouse"]: b["balance"] for b in result["closing_balances"]} == {
        "MOSE": "0", "DEPOZIT PRINCIPAL": "0"}

def test_wrong_warehouse_invoice_shows_split():
    events = [mv(1, "2026-10-02", "DEPOZIT PRINCIPAL", -100, "NT"),
              mv(2, "2026-10-02", "MOSE", 100, "NT"),
              mv(3, "2026-10-03", "DEPOZIT PRINCIPAL", -100, "F")]
    result = replay_wme_stock(events, opening_balances=OPEN)
    assert {b["warehouse"]: b["balance"] for b in result["closing_balances"]} == {
        "DEPOZIT PRINCIPAL": "-100", "MOSE": "100"}

def test_partial_mose_invoice_leaves_40():
    events = [mv(1, "2026-10-02", "DEPOZIT PRINCIPAL", -100, "NT"),
              mv(2, "2026-10-02", "MOSE", 100, "NT"),
              mv(3, "2026-10-03", "MOSE", -60, "F")]
    result = replay_wme_stock(events, opening_balances=OPEN)
    assert next(b for b in result["closing_balances"] if b["warehouse"] == "MOSE")["balance"] == "40"

def test_storno_reverses_invoice():
    events = [mv(1, "2026-10-02", "MOSE", -100, "F"),
              mv(2, "2026-10-03", "MOSE", 100, "F")]
    result = replay_wme_stock(events, opening_balances={("MOSE", "SKU", "L1"): 100})
    assert result["closing_balances"][0]["balance"] == "100"

def test_missing_lot_blocks():
    result = replay_wme_stock([mv(1, "2026-10-02", "MOSE", -10, "F", lot="")],
                              opening_balances=OPEN)
    assert result["status"] == "BLOCKED_WITH_REASON"

def test_missing_opening_blocks():
    result = replay_wme_stock([mv(1, "2026-10-02", "MOSE", -10, "F", lot="L2")],
                              opening_balances=OPEN)
    assert result["errors"][0]["reason"] == "MISSING_OPENING_BALANCE"

def test_observed_balance_disagreement():
    result = replay_wme_stock([mv(1, "2026-10-02", "MOSE", -10, "F", observed=95)],
                              opening_balances={("MOSE", "SKU", "L1"): 100})
    assert result["timeline"][0]["status"] == "WME_BALANCE_DIFFERENCE_REVIEW"

def test_duplicate_source_row_blocks():
    result = replay_wme_stock([mv(1, "2026-10-02", "MOSE", -10, "F"),
                               mv(1, "2026-10-03", "MOSE", 10, "F")],
                              opening_balances={("MOSE", "SKU", "L1"): 100})
    assert result["status"] == "BLOCKED_WITH_REASON"
