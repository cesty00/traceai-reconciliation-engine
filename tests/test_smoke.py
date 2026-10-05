import pandas as pd

from traceai_reconciliation.product_audit import round_qty, summarize_stock_report


def test_round_qty():
    assert round_qty(1.23456) == 1.235


def test_summarize_stock_report_nets_product_rows():
    df = pd.DataFrame(
        [
            {
                "CodArticol": "P1",
                "DenumireArticol": "Produs test",
                "QuantityERP": 10,
                "QuantityWMS": 7,
                "QuantityDifference": -3,
                "Gestiune": "Depozitare",
            },
            {
                "CodArticol": "P1",
                "DenumireArticol": "Produs test",
                "QuantityERP": 0,
                "QuantityWMS": 3,
                "QuantityDifference": 3,
                "Gestiune": "Receptie",
            },
        ]
    )

    audit = summarize_stock_report(df, "P1")

    assert audit.reported_stock_wme == 10
    assert audit.reported_stock_wms == 10
    assert audit.difference_reported == 0
    assert audit.verdict == "REVIEW"
