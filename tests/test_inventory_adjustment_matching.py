from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.inventory_adjustment_matching import (
    match_inventory_adjustments,
)


def test_unique_inventory_pair_is_neutralized_and_residuals_remain() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "8/28/2026 5:17:14 PM",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 1.20,
                "Cod-motiv": "INV-PLS",
            },
            {
                "Data": "9/17/2026 1:11:25 PM",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 50.00,
                "Cod-motiv": "INV-PLS",
            },
            {
                "Data": "10/10/2026 5:40:43 PM",
                "Tip operatiune": "Ajustare negativa",
                "Cantitate": -2.00,
                "Cod-motiv": "INV-MIN",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "Date": "29.08.2026",
                "OperationType": "PV",
                "Document": "PV-1",
                "Warehouse": "DEPOZIT PRINCIPAL",
                "SignedQuantity": 1.20,
            }
        ]
    )

    result = match_inventory_adjustments(wms, wme)

    assert len(result.matches) == 1
    assert result.matches[0]["quantity"] == 1.20
    assert result.residual_wms_total == 48.00
    assert result.residual_wme_total == 0.0
    assert result.system_difference_effect == 48.00
    assert result.residual_wme_pv == []


def test_multiple_wms_rows_same_day_are_aggregated_before_matching() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "8/28/2026 5:17:14 PM",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 1.10,
                "Cod-motiv": "INV-PLS",
            },
            {
                "Data": "8/28/2026 5:17:14 PM",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 0.10,
                "Cod-motiv": "INV-PLS",
            },
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "Date": "29.08.2026",
                "OperationType": "PV",
                "Document": "PV-1",
                "Warehouse": "DEPOZIT PRINCIPAL",
                "SignedQuantity": 1.20,
            }
        ]
    )

    result = match_inventory_adjustments(wms, wme)

    assert len(result.matches) == 1
    assert result.matches[0]["quantity"] == 1.20
    assert result.residual_wms_adjustments == []
    assert result.system_difference_effect == 0.0


def test_ambiguous_same_quantity_pv_is_not_force_matched() -> None:
    wms = pd.DataFrame(
        [
            {
                "Data": "8/28/2026 5:17:14 PM",
                "Tip operatiune": "Ajustare pozitiva",
                "Cantitate": 1.20,
                "Cod-motiv": "INV-PLS",
            }
        ]
    )
    wme = pd.DataFrame(
        [
            {
                "Date": "28.08.2026",
                "OperationType": "PV",
                "Document": "PV-A",
                "Warehouse": "DEPOZIT PRINCIPAL",
                "SignedQuantity": 1.20,
            },
            {
                "Date": "29.08.2026",
                "OperationType": "PV",
                "Document": "PV-B",
                "Warehouse": "DEPOZIT PRINCIPAL",
                "SignedQuantity": 1.20,
            },
        ]
    )

    result = match_inventory_adjustments(wms, wme)

    assert result.matches == []
    assert result.residual_wms_total == 1.20
    assert result.residual_wme_total == 2.40
