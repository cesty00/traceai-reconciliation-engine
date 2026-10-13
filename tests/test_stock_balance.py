from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.stock_balance import (
    wme_balance_total_at,
    wme_final_balances,
    wms_total_net_movement,
)


def test_wme_balance_total_at_uses_latest_balance_per_warehouse() -> None:
    frame = pd.DataFrame(
        [
            {
                "Date": "10.10.2026",
                "LineNo": 1,
                "Warehouse": "DP",
                "Account": "371",
                "Balance": 10.0,
            },
            {
                "Date": "11.10.2026",
                "LineNo": 2,
                "Warehouse": "DP",
                "Account": "371",
                "Balance": 12.0,
            },
            {
                "Date": "11.10.2026",
                "LineNo": 1,
                "Warehouse": "MOSE",
                "Account": "371",
                "Balance": 3.0,
            },
        ]
    )

    by_warehouse, total = wme_balance_total_at(
        frame,
        pd.Timestamp("2026-10-11 23:59:59"),
    )

    assert by_warehouse == {"DP": 12.0, "MOSE": 3.0}
    assert total == 15.0


def test_wme_balance_total_at_can_use_strict_opening_cutoff() -> None:
    frame = pd.DataFrame(
        [
            {
                "Date": "10.10.2026",
                "LineNo": 1,
                "Warehouse": "DP",
                "Balance": 10.0,
            },
            {
                "Date": "11.10.2026",
                "LineNo": 2,
                "Warehouse": "DP",
                "Balance": 12.0,
            },
        ]
    )

    by_warehouse, total = wme_balance_total_at(
        frame,
        pd.Timestamp(year=2026, month=10, day=11),
        strictly_before=True,
    )

    assert by_warehouse == {"DP": 10.0}
    assert total == 10.0


def test_wme_final_balances_returns_latest_known_balances() -> None:
    frame = pd.DataFrame(
        [
            {
                "Date": "10.10.2026",
                "LineNo": 1,
                "Warehouse": "DP",
                "Balance": 10.0,
            },
            {
                "Date": "11.10.2026",
                "LineNo": 2,
                "Warehouse": "DP",
                "Balance": 12.0,
            },
        ]
    )

    by_warehouse, total = wme_final_balances(frame)

    assert by_warehouse == {"DP": 12.0}
    assert total == 12.0


def test_wms_total_net_movement_counts_external_stock_effects_only() -> None:
    frame = pd.DataFrame(
        [
            {"TipOperatie": "Receptie", "Cantitate": 10.0},
            {"TipOperatie": "Livrare", "Cantitate": -4.0},
            {"TipOperatie": "Mutare", "Cantitate": -50.0},
            {"TipOperatie": "Mutare intre gestiuni", "Cantitate": 50.0},
        ]
    )

    movement, unknown = wms_total_net_movement(frame)

    assert movement == 6.0
    assert unknown == []


def test_wms_total_net_movement_fails_closed_on_unknown_operation() -> None:
    frame = pd.DataFrame(
        [
            {"TipOperatie": "Receptie", "Cantitate": 10.0},
            {"TipOperatie": "OPERATIE_NECUNOSCUTA", "Cantitate": 2.0},
        ]
    )

    movement, unknown = wms_total_net_movement(frame)

    assert movement is None
    assert unknown == ["OPERATIE_NECUNOSCUTA"]


def test_stock_balance_helpers_handle_empty_frames() -> None:
    empty = pd.DataFrame()

    assert wme_final_balances(empty) == ({}, None)
    assert wms_total_net_movement(empty) == (0.0, [])
