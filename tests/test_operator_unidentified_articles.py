import pandas as pd
from traceai_reconciliation.operator_stock_view import build_product_list, split_unidentified_articles


def test_realistic_unmapped_rows_quarantined_and_normal_products_visible():
    report = pd.DataFrame([
        {"CodArticol": "10002", "DenumireArticol": "CUTIE FRESH", "QuantityWMS": 6090, "QuantityERP": 6962, "QuantityDifference": -872, "Gestiune": "Depozitare"},
        {"CodArticol": None, "DenumireArticol": "NEDEFINIT IN WMS", "QuantityWMS": 0, "QuantityERP": 1143, "QuantityDifference": -1143, "Gestiune": "Depozitare"},
        {"CodArticol": "10002", "DenumireArticol": "CUTIE FRESH", "QuantityWMS": 166.98, "QuantityERP": 166.98, "QuantityDifference": 0, "Gestiune": "SECTIE PRODUCTIE"},
        {"CodArticol": None, "DenumireArticol": "NEDEFINIT IN WMS", "QuantityWMS": 0, "QuantityERP": 77197, "QuantityDifference": -77197, "Gestiune": "SECTIE PRODUCTIE"},
    ])
    identifiable, unmatched = split_unidentified_articles(report)
    assert len(unmatched) == 2
    assert unmatched["QuantityERP"].sum() == 78340
    products = build_product_list(identifiable)
    assert products.iloc[0]["CodArticol"] == "10002"
    assert products.iloc[0]["Diferenta_WMS_minus_WME"] == -872
    assert bool(products.iloc[0]["Concordanta_cu_raportul"])


def test_whitespace_article_code_quarantined():
    report = pd.DataFrame([{"CodArticol": " ", "DenumireArticol": "NEDEFINIT", "QuantityWMS": 0, "QuantityERP": 1}])
    identifiable, unmatched = split_unidentified_articles(report)
    assert identifiable.empty
    assert len(unmatched) == 1
