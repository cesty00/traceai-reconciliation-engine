from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.wme_residual_matching import (
    match_wme_residual_movements,
)


def test_wme_residual_movements_report_nonstandard_stock_effect() -> None:
    wme = pd.DataFrame(
        [
            {
                "OperationType": "F",
                "Document": "48462",
                "SignedQuantity": 1.0,
                "Warehouse": "DEPOZIT PESTE PROASPAT",
            },
            {
                "OperationType": "PV",
                "Document": "2301",
                "SignedQuantity": -0.5,
                "Warehouse": "DEPOZIT PESTE PROASPAT",
            },
            {
                "OperationType": "AE",
                "Document": "115000",
                "SignedQuantity": -100.0,
                "Warehouse": "DEPOZIT PESTE PROASPAT",
            },
        ]
    )

    result = match_wme_residual_movements(wme)

    assert result.wme_signed_total == 0.5
    assert result.system_difference_effect == -0.5
    assert len(result.residual_movements) == 2


def test_wme_residual_movements_exclude_special_warehouses() -> None:
    wme = pd.DataFrame(
        [
            {
                "OperationType": "F",
                "Document": "100",
                "SignedQuantity": -10.0,
                "Warehouse": "DETERIORATE",
            },
            {
                "OperationType": "PV",
                "Document": "101",
                "SignedQuantity": 2.0,
                "Warehouse": "MOSTRE",
            },
        ]
    )

    result = match_wme_residual_movements(
        wme,
        excluded_warehouses={"DETERIORATE", "PROTAN", "MOSTRE"},
    )

    assert result.residual_movements == []
    assert result.wme_signed_total == 0.0
    assert result.system_difference_effect == 0.0
