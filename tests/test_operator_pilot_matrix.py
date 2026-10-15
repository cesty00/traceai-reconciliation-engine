import pandas as pd
import pytest
from traceai_reconciliation.operator_pilot_matrix import build_pilot_sample


def test_sample_includes_both_directions_and_zero():
    products = pd.DataFrame([
        {"CodArticol": "N1", "Diferenta_WMS_minus_WME": -872},
        {"CodArticol": "N2", "Diferenta_WMS_minus_WME": -1},
        {"CodArticol": "P1", "Diferenta_WMS_minus_WME": 10},
        {"CodArticol": "P2", "Diferenta_WMS_minus_WME": 5},
        {"CodArticol": "Z1", "Diferenta_WMS_minus_WME": 0},
        {"CodArticol": "Z2", "Diferenta_WMS_minus_WME": 0},
    ])
    sample = build_pilot_sample(products, per_category=1)
    assert set(sample["Tip_test"]) == {"ZERO", "WME_MAI_MARE", "WMS_MAI_MARE"}
    assert sample.loc[sample["Tip_test"] == "WME_MAI_MARE", "CodArticol"].item() == "N1"
    assert sample["Stadiu_QA"].eq("NETESTAT").all()


def test_no_automatic_success_when_balance_zero():
    sample = build_pilot_sample(pd.DataFrame([
        {"CodArticol": "X", "Diferenta_WMS_minus_WME": 0.0}
    ]))
    assert sample.iloc[0]["Tip_test"] == "ZERO"
    assert sample.iloc[0]["Stadiu_QA"] == "NETESTAT"


def test_fail_closed_invalid_input():
    with pytest.raises(ValueError):
        build_pilot_sample(pd.DataFrame([
            {"CodArticol": None, "Diferenta_WMS_minus_WME": 1}
        ]))
