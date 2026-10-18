from traceai_reconciliation.investigation.operation_timeline import _identifier_text

def test_integral_pallet_identifiers_do_not_gain_float_suffix():
    assert _identifier_text(268045.0, "pallet") == "268045"
    assert _identifier_text("268045.0", "pallet") == "268045"
    assert _identifier_text("268045", "pallet") == "268045"
    assert _identifier_text("000268045", "pallet") == "000268045"

def test_non_integral_and_non_pallet_values_are_not_fabricated():
    assert _identifier_text("268045.5", "pallet") == "268045.5"
    assert _identifier_text("6042047601", "lot") == "6042047601"
