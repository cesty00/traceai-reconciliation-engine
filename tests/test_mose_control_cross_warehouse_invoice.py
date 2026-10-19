from traceai_reconciliation.mose_control.cross_warehouse_invoice import cross_warehouse_invoice_exits


def row(warehouse, source_row, qty=-10, client="FISHERMEN INN S.R.L."):
    return dict(operation_type="F", document="91655", date="2026-03-11",
                product_name="FILE CRAP CU PIELE 300-500G, BAX 10KG VRAC",
                partner=client, unit="KG", quantity=qty,
                warehouse=warehouse, source_row=source_row)


def test_real_document_91655_two_warehouses_flags_double_stock_exit():
    issues = cross_warehouse_invoice_exits([
        row("DEPOZIT PRINCIPAL", 71944),
        row("MOSE", 72103),
    ])
    assert len(issues) == 1
    assert issues[0]["status"] == "MULTI_WAREHOUSE_SAME_F_EXIT_REVIEW"
    assert issues[0]["quantity_by_warehouse"] == {"DEPOZIT PRINCIPAL": "-10", "MOSE": "-10"}
    assert issues[0]["verdict"] == "REVIEW"


def test_one_warehouse_with_two_lots_is_not_multi_warehouse():
    assert cross_warehouse_invoice_exits([
        row("MOSE", 100, -5), row("MOSE", 101, -5)
    ]) == []


def test_different_clients_not_merged():
    assert cross_warehouse_invoice_exits([
        row("MOSE", 100), row("DEPOZIT PRINCIPAL", 101, client="OTHER CLIENT")
    ]) == []


def test_reversal_positive_entry_not_double_exit():
    assert cross_warehouse_invoice_exits([
        row("MOSE", 100, 10), row("DEPOZIT PRINCIPAL", 101, -10)
    ]) == []
