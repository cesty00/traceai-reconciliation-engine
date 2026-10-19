from traceai_reconciliation.mose_control.stock_after_invoice import (
    check_invoice_stock, explain_warehouse_allocation,
)


def f(**kwargs):
    row = dict(operation_type="F", warehouse="MOSE", product_code="SKU",
               source_row=123, document="F100", quantity="-60")
    row.update(kwargs)
    return row


def test_partial_invoice_leaves_40_in_mose():
    result = check_invoice_stock(invoice=f(), before_balance=100, after_balance=40)
    assert result["status"] == "WME_BALANCE_ARITHMETIC_OK_REVIEW"
    assert result["expected_after"] == "40"


def test_wrong_after_balance_is_reported_not_corrected():
    result = check_invoice_stock(invoice=f(), before_balance=100, after_balance=45)
    assert result["status"] == "WME_BALANCE_INCONSISTENCY_REVIEW"
    assert result["delta"] == "5"


def test_missing_before_balance_fails_closed():
    assert check_invoice_stock(invoice=f(), before_balance=None, after_balance=40)["status"] == "MISSING_BALANCE_EVIDENCE_REVIEW"


def test_no_invoice_source_row_fails_closed():
    assert check_invoice_stock(invoice=f(source_row=None), before_balance=100, after_balance=40)["status"] == "INCOMPLETE_INVOICE_SCOPE_REVIEW"


def test_correct_transfer_and_invoice_from_mose():
    result = explain_warehouse_allocation(principal_before=100, mose_before=0,
                 transfer_quantity=100, invoice_quantity=100, invoice_warehouse="MOSE")
    assert result["principal_after"] == "0"
    assert result["mose_after"] == "0"


def test_wrong_warehouse_invoice_can_hide_in_total():
    result = explain_warehouse_allocation(principal_before=100, mose_before=0,
                 transfer_quantity=100, invoice_quantity=100, invoice_warehouse="DEPOZIT PRINCIPAL")
    assert result["principal_after"] == "-100"
    assert result["mose_after"] == "100"
    assert result["total_after"] == "0"
    assert result["verdict"] == "REVIEW"


def test_direct_delivery_no_nt():
    result = explain_warehouse_allocation(principal_before=100, mose_before=0,
                 transfer_quantity=0, invoice_quantity=100, invoice_warehouse="DEPOZIT PRINCIPAL")
    assert (result["principal_after"], result["mose_after"]) == ("0", "0")


def test_unknown_warehouse_not_assumed_mose():
    assert explain_warehouse_allocation(principal_before=100, mose_before=0,
            transfer_quantity=100, invoice_quantity=100,
            invoice_warehouse="MOSTRE")["status"] == "OTHER_WAREHOUSE_REVIEW"
