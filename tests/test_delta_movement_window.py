from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from traceai_reconciliation.investigation.delta_movement_window import (
    MovementWindow,
    build_delta_movement_window,
    filter_frame_to_window,
)
from traceai_reconciliation.investigation.source_index import SQLiteSourceIndex


def test_filter_frame_to_window_uses_open_closed_interval() -> None:
    frame = pd.DataFrame(
        [
            {"Date": "2026-10-11 20:00:00", "value": "previous"},
            {"Date": "2026-10-11 20:00:01", "value": "inside"},
            {"Date": "2026-10-12 20:00:00", "value": "current"},
            {"Date": "2026-10-12 20:00:01", "value": "after"},
        ]
    )
    window = MovementWindow.from_values(
        "2026-10-11 20:00:00",
        "2026-10-12 20:00:00",
    )

    result = filter_frame_to_window(frame, window)

    assert result["value"].tolist() == ["inside", "current"]


def test_filter_frame_to_window_fails_closed_without_date() -> None:
    frame = pd.DataFrame([{"Document": "X"}])
    window = MovementWindow.from_values(
        "2026-10-11 20:00:00",
        "2026-10-12 20:00:00",
    )

    with pytest.raises(ValueError, match="operation date"):
        filter_frame_to_window(frame, window)


def test_filter_frame_to_window_fails_closed_on_invalid_date() -> None:
    frame = pd.DataFrame(
        [
            {"Date": "2026-10-12 10:00:00"},
            {"Date": "not-a-date"},
        ]
    )
    window = MovementWindow.from_values(
        "2026-10-11 20:00:00",
        "2026-10-12 20:00:00",
    )

    with pytest.raises(ValueError, match="invalid operation date"):
        filter_frame_to_window(frame, window)


class FakeIndex:
    def read_wms_product(self, product_code: str):
        assert product_code == "DS099904475"
        return pd.DataFrame(
            [
                {"Data": "2026-10-11 19:00:00", "Cantitate": 10.0},
                {"Data": "2026-10-12 10:00:00", "Cantitate": -1.44},
            ]
        )

    def read_wme_product(self, product_name: str):
        assert product_name == "Produs test"
        return (
            pd.DataFrame(
                [
                    {"Date": "2026-10-11 19:00:00", "SignedQuantity": 10.0},
                ]
            ),
            {"WME-1"},
        )

    def read_production_product(self, product_code: str):
        assert product_code == "DS099904475"
        return pd.DataFrame(
            [
                {"Data Start": "2026-10-12 12:00:00", "Qty": 2.0},
            ]
        )


def test_build_delta_movement_window_collects_only_new_movements() -> None:
    result = build_delta_movement_window(
        source_index=FakeIndex(),
        product_code="DS099904475",
        product_name="Produs test",
        start_exclusive="2026-10-11 20:00:00",
        end_inclusive="2026-10-12 20:00:00",
    )

    assert result.wms_count == 1
    assert result.wme_count == 0
    assert result.production_count == 1
    assert result.wms_rows[0]["Cantitate"] == -1.44
    assert result.production_rows[0]["Qty"] == 2.0


def test_movement_window_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="start_exclusive < end_inclusive"):
        MovementWindow.from_values(
            "2026-10-12 20:00:00",
            "2026-10-11 20:00:00",
        )
