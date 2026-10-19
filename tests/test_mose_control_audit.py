from traceai_reconciliation.mose_control import audit_mose_flows


def f(warehouse, user="MOSE", document="F-01", product="SKU"):
    return dict(system="WME", operation_type="F", warehouse=warehouse,
                document=document, product_code=product, quantity=-10,
                actor={"user": user}, source_row=100)


def nt():
    return dict(system="WME", operation_type="NT", warehouse="DEPOZIT PRINCIPAL",
                counterpart="MOSE", document="NT-01", product_code="SKU", quantity=-10)


def delivery(document):
    return dict(system="WMS", operation_type="Livrare", document=document,
                product_code="SKU", quantity=-10)


def test_transfer_followed_by_f_invoice_from_mose_stays_review():
    result = audit_mose_flows([nt(), f("MOSE")], [delivery("TRANSFER_MOSE-01")])
    assert len(result.findings) == 1
    assert result.findings[0]["status"] == "MOSE_F_INVOICE_REVIEW"
    assert result.findings[0]["verdict"] == "REVIEW"


def test_direct_delivery_from_principal_never_auto_matches():
    result = audit_mose_flows([f("DEPOZIT PRINCIPAL")], [delivery("SFA123")])
    assert result.findings[0]["status"] == "DIRECT_DELIVERY_REVIEW"
    assert len(result.findings[0]["wms_delivery_candidates"]) == 1


def test_transfer_then_invoice_principal_warns_not_confirms_error():
    result = audit_mose_flows([nt(), f("DEPOZIT PRINCIPAL")], [delivery("TRANSFER_MOSE-01")])
    assert result.findings[0]["status"] == "WAREHOUSE_CONFLICT_REVIEW"
    assert result.findings[0]["verdict"] == "REVIEW"


def test_warehouse_scoped_even_when_different_actor():
    result = audit_mose_flows([f("MOSE", user="ANOTHER")], [])
    assert result.findings[0]["scope"] == {"user_mose": False, "warehouse_mose": True}


def test_customer_mose_business_distribution_is_not_warehouse():
    row = f("DEPOZIT PRINCIPAL", user="OTHER")
    row["counterpart"] = "MOSE Business Distribution"
    assert not audit_mose_flows([row], []).findings


def test_missing_nt_or_wms_not_fabricated_as_match():
    finding = audit_mose_flows([f("MOSE")], []).findings[0]
    assert finding["nt_candidates"] == []
    assert finding["wms_delivery_candidates"] == []
    assert finding["verdict"] == "REVIEW"


def test_direct_delivery_policy_does_not_require_nt():
    finding = audit_mose_flows([f("DEPOZIT PRINCIPAL")], [delivery("SFA123")]).findings[0]
    assert finding["status"] == "DIRECT_DELIVERY_REVIEW"
    assert "fara TRANSFER_MOSE/NT" in finding["recommendation"]
    assert finding["nt_candidates"] == []
    assert finding["verdict"] == "REVIEW"


def test_conflict_prefers_correction_a_and_b_is_emergency_only():
    finding = audit_mose_flows([nt(), f("DEPOZIT PRINCIPAL")],
                               [delivery("TRANSFER_MOSE-01")]).findings[0]
    assert finding["status"] == "WAREHOUSE_CONFLICT_REVIEW"
    assert finding["recommendation"].index("A (preferata)") < finding["recommendation"].index("B (avarie)")
    assert "aprobare umana" in finding["recommendation"]


def test_no_delivery_does_not_prove_direct_invoice_valid():
    finding = audit_mose_flows([f("DEPOZIT PRINCIPAL")], []).findings[0]
    assert finding["verdict"] == "REVIEW"
    assert finding["wms_delivery_candidates"] == []
