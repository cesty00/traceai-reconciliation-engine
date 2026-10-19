from traceai_reconciliation.mose_control.invoice_warehouse_policy import multi_warehouse_invoice_exits

def e(wh, prod, n, doc="123", day="11.03.2026"):
    return dict(operation_type="F", document=doc, date=day,
                product_name=prod, partner="CLIENT", warehouse=wh,
                quantity=-3, source_row=n, unit="KG")

def test_different_products_two_warehouses_are_detected():
    cases = multi_warehouse_invoice_exits([e("MOSE", "A", 4),
                                          e("DEPOZIT PRINCIPAL", "B", 5)])
    assert len(cases) == 1
    assert cases[0]["source_rows"] == [4, 5]
    assert cases[0]["status"] == "INVOICE_MULTI_WAREHOUSE_REVIEW"

def test_many_products_single_warehouse_are_not_flagged():
    assert multi_warehouse_invoice_exits([e("MOSE", "A", 4), e("MOSE", "B", 5)]) == []

def test_different_invoices_not_combined():
    assert multi_warehouse_invoice_exits([e("MOSE", "A", 4),
            e("DEPOZIT PRINCIPAL", "B", 5, doc="124")]) == []

def test_positive_reversal_not_stock_exit():
    r=e("DEPOZIT PRINCIPAL", "B", 5)
    r["quantity"]=3
    assert multi_warehouse_invoice_exits([e("MOSE", "A", 4), r]) == []
