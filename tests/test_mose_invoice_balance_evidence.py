from traceai_reconciliation.mose_control.invoice_balance_evidence import invoice_balance_evidence

def row(warehouse, source_row, quantity, balance):
    return dict(warehouse=warehouse, source_row=source_row, quantity=quantity,
                reported_balance=balance, unit="KG")

def test_two_warehouses_preserved_separately():
    result = invoice_balance_evidence([
        row("DEPOZIT PRINCIPAL", 71944, -10, 6560),
        row("MOSE", 72103, -10, 0),
    ])
    assert result["status"] == "ROW_BALANCES_EXTRACTED_REVIEW"
    assert [(x["warehouse"], x["balance_before_this_line"], x["balance_after_this_line"])
            for x in result["records"]] == [
        ("DEPOZIT PRINCIPAL", "6570", "6560"), ("MOSE", "10", "0")]
    assert result["verdict"] == "REVIEW"

def test_reverse_signed_invoice_increases_balance():
    result = invoice_balance_evidence([row("MOSE", 5, 10, 100)])
    assert result["records"][0]["balance_before_this_line"] == "90"

def test_missing_reported_balance_does_not_invent_stock():
    result = invoice_balance_evidence([row("MOSE", 5, -10, None)])
    assert result["status"] == "INCOMPLETE_BALANCE_EVIDENCE_REVIEW"
    assert result["records"] == []

def test_quantity_string_parsed_exactly():
    result = invoice_balance_evidence([row("MOSE", 7, "-0.125", "1.375")])
    assert result["records"][0]["balance_before_this_line"] == "1.500"
