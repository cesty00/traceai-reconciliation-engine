from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.stock_report_zone_matching import (
    reconcile_stock_report_zones,
)


def test_mostre_erp_zero_is_report_mapping_when_wms_equals_wme() -> None:
    stock_rows = pd.DataFrame(
        [
            {
                "Gestiune": "Depozitare",
                "QuantityERP": 553.0,
                "QuantityWMS": 313.0,
                "QuantityDifference": -240.0,
            },
            {
                "Gestiune": "MOSTRE",
                "QuantityERP": 0.0,
                "QuantityWMS": 1.0,
                "QuantityDifference": 1.0,
            },
        ]
    )

    result = reconcile_stock_report_zones(
        stock_rows,
        {
            "DEPOZIT PRINCIPAL": 553.0,
            "MOSTRE": 1.0,
        },
    )

    assert result.mapping_effect_total == 1.0
    assert len(result.confirmed_report_mapping_rows) == 1
    confirmed = result.confirmed_report_mapping_rows[0]
    assert confirmed["report_warehouse"] == "MOSTRE"
    assert confirmed["actual_system_difference"] == 0.0
    assert confirmed["report_mapping_effect"] == 1.0
    assert confirmed["status"] == "REPORT_ERP_ZERO_MAPPING_CONFIRMED"

    depozitare = result.rows[0]
    assert depozitare["actual_system_difference"] == -240.0
    assert depozitare["report_mapping_effect"] == 0.0
    assert depozitare["status"] == "MAPPED"


def test_erp_zero_special_zone_is_not_auto_confirmed_when_wms_differs_from_wme() -> None:
    stock_rows = pd.DataFrame(
        [
            {
                "Gestiune": "DETERIORATE",
                "QuantityERP": 0.0,
                "QuantityWMS": 10.0,
                "QuantityDifference": 10.0,
            }
        ]
    )

    result = reconcile_stock_report_zones(
        stock_rows,
        {"DETERIORATE": 8.0},
    )

    assert result.mapping_effect_total == 0.0
    assert result.confirmed_report_mapping_rows == []
    assert result.rows[0]["actual_system_difference"] == 2.0
    assert result.rows[0]["report_mapping_effect"] == 8.0
    assert result.rows[0]["status"] == "REPORT_MAPPING_REVIEW"


def test_peste_proaspat_maps_to_depozit_peste_proaspat() -> None:
    stock_rows = pd.DataFrame(
        [
            {
                "Gestiune": "PESTE PROASPAT",
                "QuantityERP": 651.0,
                "QuantityWMS": 0.0,
                "QuantityDifference": -651.0,
            }
        ]
    )

    result = reconcile_stock_report_zones(
        stock_rows,
        {"DEPOZIT PESTE PROASPAT": 651.0},
    )

    assert result.mapping_effect_total == 0.0
    assert result.rows[0]["actual_system_difference"] == -651.0
    assert result.rows[0]["status"] == "MAPPED"
