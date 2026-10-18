import pandas as pd
import pytest

from traceai_reconciliation.operator_stock_view import build_product_list


def test_lists_zero_and_nonzero_and_aggregates_warehouses():
    report = pd.DataFrame([
        {"CodArticol": "10002", "DenumireArticol": "Cutie", "QuantityWMS": 10, "QuantityERP": 12, "QuantityDifference": -2},
        {"CodArticol": "10002", "DenumireArticol": "Cutie", "QuantityWMS": 5, "QuantityERP": 3, "QuantityDifference": 2},
        {"CodArticol": "00005", "DenumireArticol": "Altul", "QuantityWMS": 7, "QuantityERP": 5, "QuantityDifference": 2},
    ])
    result = build_product_list(report).set_index("CodArticol")
    assert set(result.index) == {"10002", "00005"}
    assert result.loc["10002", "Diferenta_WMS_minus_WME"] == 0
    assert result.loc["00005", "Diferenta_WMS_minus_WME"] == 2
    assert result["Concordanta_cu_raportul"].all()


def test_source_report_disagreement_visible_not_silenced():
    report = pd.DataFrame([{"CodArticol": "1", "DenumireArticol": "A", "QuantityWMS": 8, "QuantityERP": 3, "QuantityDifference": 0}])
    result = build_product_list(report)
    assert result.iloc[0]["Diferenta_WMS_minus_WME"] == 5
    assert not bool(result.iloc[0]["Concordanta_cu_raportul"])


@pytest.mark.parametrize("field,value", [
    ("QuantityWMS", "not-a-number"),
    ("QuantityERP", None),
    ("CodArticol", None),
])
def test_invalid_data_fails_closed(field, value):
    row = {"CodArticol": "1", "DenumireArticol": "A", "QuantityWMS": 2, "QuantityERP": 1}
    row[field] = value
    with pytest.raises(ValueError):
        build_product_list(pd.DataFrame([row]))
