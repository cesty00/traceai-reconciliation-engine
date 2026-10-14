"""Real-event regression for item 10002, source exports dated 2026-10-11.

The rows below are copied from the product-specific WMS and WME extracts.
This test fixes the documented arithmetic attribution, NOT an operational
finding that a correction is required. WME F and PV remain REVIEW.
"""
import pandas as pd
import pytest


def test_real_10002_post_alignment_exception_events():
    # WMS COR STOC entries on June 26 and June 30, 2026.
    wms_adjustments = pd.DataFrame([
        {"date": "2026-06-26 07:03:15", "quantity": -450.0, "reason": "COR STOC", "note": "DIFERENTA PROVENITA INVENTAR 05.06.26"},
        {"date": "2026-06-26 07:03:31", "quantity": -450.0, "reason": "COR STOC", "note": "DIFERENTA PROVENITA INVENTAR 05.06.26"},
        {"date": "2026-06-26 07:03:50", "quantity": -450.0, "reason": "COR STOC", "note": "DIFERENTA PROVENITA INVENTAR 05.06.26"},
        {"date": "2026-06-30 13:55:03", "quantity": 1.0, "reason": "COR STOC", "note": ""},
    ])
    # Internal WMS movements are not stock creation.
    wms_internal_moves = pd.DataFrame([
        {"date": "2026-06-26 10:54:44", "quantity": 450.0, "type": "Mutare intre gestiuni"},
        {"date": "2026-06-26 13:15:57", "quantity": 450.0, "type": "Mutare intre gestiuni"},
        {"date": "2026-06-30 13:56:03", "quantity": 1.0, "type": "Mutare intre gestiuni"},
    ])
    # WME F and PV appear in the actual ERP extract, not the WMS extract.
    wme_adjustments = pd.DataFrame([
        {"date": "2026-07-08", "document": "6009708", "type": "F", "quantity": -232.0, "note": "AdminWMEcuETrans"},
        {"date": "2026-07-23", "document": "2557", "type": "PV", "quantity": -245.0, "note": "PRODUCTIE"},
    ])

    wms_minus_wme = (
        wms_adjustments["quantity"].sum()
        - wme_adjustments["quantity"].sum()
    )
    assert len(wms_adjustments) == 4
    assert len(wms_internal_moves) == 3
    assert wms_adjustments["quantity"].sum() == pytest.approx(-1349.0)
    assert wme_adjustments["quantity"].sum() == pytest.approx(-477.0)
    assert wms_minus_wme == pytest.approx(-872.0)
    assert set(wme_adjustments["type"]) == {"F", "PV"}


def test_real_10002_pv_2552_is_a_match_after_erp_aggregation():
    # PV 2552 has separate Warehouse lines, which must be netted first.
    wme_lines = [-349.0001, -0.9999]
    wms_correction = -350.0
    assert sum(wme_lines) == pytest.approx(wms_correction)
