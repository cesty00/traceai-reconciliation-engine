from __future__ import annotations

import pandas as pd

from traceai_reconciliation.investigation.source_readers import (
    filter_by_period,
    parse_operational_dates,
)


def test_wms_slash_dates_are_month_first() -> None:
    parsed = parse_operational_dates(
        pd.Series(
            [
                "2/12/2026 3:26:38 PM",
                "3/12/2026 1:50:59 PM",
            ]
        )
    )

    assert parsed.iloc[0] == pd.Timestamp("2026-02-12 15:26:38")
    assert parsed.iloc[1] == pd.Timestamp("2026-03-12 13:50:59")


def test_wme_dotted_dates_are_day_first() -> None:
    parsed = parse_operational_dates(
        pd.Series(["11.10.2026", "29.08.2026"])
    )

    assert parsed.iloc[0] == pd.Timestamp("2026-10-11")
    assert parsed.iloc[1] == pd.Timestamp("2026-08-29")


def test_period_filter_keeps_february_wms_row_not_december() -> None:
    frame = pd.DataFrame(
        [
            {
                "Data": "2/12/2026 3:26:38 PM",
                "value": "feb-12",
            },
            {
                "Data": "12/2/2026 3:26:38 PM",
                "value": "dec-2",
            },
        ]
    )

    result = filter_by_period(
        frame,
        "01.01.2026-11.10.2026",
    )

    assert result["value"].tolist() == ["feb-12"]
