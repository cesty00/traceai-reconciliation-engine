from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from .source_index import SQLiteSourceIndex
from .source_readers import resolve_column


@dataclass(frozen=True, slots=True)
class MovementWindow:
    start_exclusive: pd.Timestamp
    end_inclusive: pd.Timestamp

    @classmethod
    def from_values(
        cls,
        start_exclusive: str | datetime | pd.Timestamp,
        end_inclusive: str | datetime | pd.Timestamp,
    ) -> "MovementWindow":
        start = pd.Timestamp(start_exclusive)
        end = pd.Timestamp(end_inclusive)
        if start >= end:
            raise ValueError(
                "Delta movement window requires start_exclusive < end_inclusive."
            )
        return cls(start_exclusive=start, end_inclusive=end)


@dataclass(frozen=True, slots=True)
class DeltaMovementWindowResult:
    product_code: str
    product_name: str
    start_exclusive: str
    end_inclusive: str
    wms_count: int
    wme_count: int
    production_count: int
    wms_rows: tuple[dict[str, Any], ...]
    wme_rows: tuple[dict[str, Any], ...]
    production_rows: tuple[dict[str, Any], ...]


def _normalize_timestamp(value: pd.Timestamp) -> pd.Timestamp:
    if value.tzinfo is not None:
        return value.tz_convert("UTC").tz_localize(None)
    return value


def filter_frame_to_window(
    frame: pd.DataFrame,
    window: MovementWindow,
) -> pd.DataFrame:
    """Return rows with operation date in (start_exclusive, end_inclusive].

    A missing date column is unsafe for delta analysis and therefore fails
    closed instead of returning the full frame.
    """
    if frame.empty:
        return frame.copy()

    date_column = resolve_column(frame.columns, "date", required=False)
    if date_column is None:
        raise ValueError(
            "Delta movement window cannot resolve an operation date column."
        )

    parsed = pd.to_datetime(
        frame[date_column],
        errors="coerce",
        dayfirst=True,
        utc=True,
    ).dt.tz_convert(None)

    if parsed.isna().any():
        invalid = int(parsed.isna().sum())
        raise ValueError(
            "Delta movement window found "
            f"{invalid} row(s) with an invalid operation date."
        )

    start = _normalize_timestamp(window.start_exclusive)
    end = _normalize_timestamp(window.end_inclusive)
    mask = parsed.gt(start) & parsed.le(end)

    result = frame.loc[mask].copy()
    result[date_column] = parsed.loc[mask]
    return result


def _records(frame: pd.DataFrame) -> tuple[dict[str, Any], ...]:
    if frame.empty:
        return ()
    normalized = frame.copy()
    for column in normalized.columns:
        if pd.api.types.is_datetime64_any_dtype(normalized[column]):
            normalized[column] = normalized[column].map(
                lambda value: value.isoformat()
                if pd.notna(value)
                else None
            )
    return tuple(normalized.to_dict(orient="records"))


def build_delta_movement_window(
    *,
    source_index: SQLiteSourceIndex,
    product_code: str,
    product_name: str,
    start_exclusive: str | datetime | pd.Timestamp,
    end_inclusive: str | datetime | pd.Timestamp,
) -> DeltaMovementWindowResult:
    """Load one product and retain only movements added in the delta window.

    This component performs no matching and does not infer a root cause. It is
    intentionally limited to deterministic extraction of the WMS, WME and
    production candidate movements that occurred after the previous snapshot
    and up to the current snapshot.
    """
    code = str(product_code).strip()
    name = str(product_name).strip()
    if not code:
        raise ValueError("product_code is required.")
    if not name:
        raise ValueError("product_name is required.")

    window = MovementWindow.from_values(start_exclusive, end_inclusive)

    wms = filter_frame_to_window(
        source_index.read_wms_product(code),
        window,
    )
    wme_frame, _ = source_index.read_wme_product(name)
    wme = filter_frame_to_window(wme_frame, window)
    production = filter_frame_to_window(
        source_index.read_production_product(code),
        window,
    )

    return DeltaMovementWindowResult(
        product_code=code,
        product_name=name,
        start_exclusive=window.start_exclusive.isoformat(),
        end_inclusive=window.end_inclusive.isoformat(),
        wms_count=len(wms),
        wme_count=len(wme),
        production_count=len(production),
        wms_rows=_records(wms),
        wme_rows=_records(wme),
        production_rows=_records(production),
    )
