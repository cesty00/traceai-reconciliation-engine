from traceai_reconciliation.mose_control.single_warehouse_operator_screen import mose_user_dp_invoice_reviews

def f(warehouse,user,doc="100",product="A"):
    return {"document":doc,"date":"11.03.2026","partner":"CUSTOMER",
      "warehouse":warehouse,"user":user,"product_name":product,
      "quantity":-10.0,"source_row":10 if product=="A" else 11,
      "operation_type":"F"}

def test_mose_user_direct_dp_is_neutral_wms_check():
    x=mose_user_dp_invoice_reviews([f("DEPOZIT PRINCIPAL","MOSE")])
    assert len(x)==1 and x[0]["status"]=="MOSE_USER_DIRECT_DP_INVOICE_WMS_CHECK_REVIEW"

def test_other_operator_is_not_mose_case():
    assert mose_user_dp_invoice_reviews([f("DEPOZIT PRINCIPAL","ALICE")])==[]

def test_invoice_issued_in_mose_does_not_trigger_dp_check():
    assert mose_user_dp_invoice_reviews([f("MOSE","MOSE")])==[]

def test_two_warehouses_not_classified_single_dp():
    assert mose_user_dp_invoice_reviews([f("DEPOZIT PRINCIPAL","MOSE"),f("MOSE","MOSE",product="B")])==[]
