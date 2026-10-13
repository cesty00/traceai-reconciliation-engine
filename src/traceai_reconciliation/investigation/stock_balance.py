from __future__ import annotations

import pandas as pd

from .source_readers import resolve_column


def wme_balance_total_at(
    wme_rows: pd.DataFrame,
    cutoff: pd.Timestamp,
    strictly_before: bool = False,
) -> tuple[dict[str, float], float | None]:
    if wme_rows.empty:
        return {}, None

    work = wme_rows.copy()
    work["Date"] = pd.to_datetime(work["Date"], errors="coerce", dayfirst=True)
    work["LineNo"] = pd.to_numeric(work["LineNo"], errors="coerce")
    work["Balance"] = pd.to_numeric(work["Balance"], errors="coerce")

    if strictly_before:
        work = work[work["Date"] < cutoff]
    else:
        work = work[work["Date"] <= cutoff]

    group_keys = ["Warehouse"]
    if "Account" in work.columns:
        group_keys.append("Account")

    balances_by_warehouse: dict[str, float] = {}
    for keys, group in work.groupby(group_keys, dropna=False):
        ordered = group.sort_values(["Date", "LineNo"], na_position="first")
        balances = ordered["Balance"].dropna()
        if balances.empty:
            continue
        warehouse = keys[0] if isinstance(keys, tuple) else keys
        balances_by_warehouse[str(warehouse)] = (
            balances_by_warehouse.get(str(warehouse), 0.0)
            + float(balances.iloc[-1])
        )

    if not balances_by_warehouse:
        return {}, None
    return balances_by_warehouse, float(sum(balances_by_warehouse.values()))


def wme_final_balances(
    wme_rows: pd.DataFrame,
) -> tuple[dict[str, float], float | None]:
    if wme_rows.empty:
        return {}, None
    dates = pd.to_datetime(wme_rows["Date"], errors="coerce", dayfirst=True)
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return {}, None
    return wme_balance_total_at(
        wme_rows,
        valid_dates.max(),
        strictly_before=False,
    )


def wms_total_net_movement(
    wms_rows: pd.DataFrame,
) -> tuple[float | None, list[str]]:
    if wms_rows.empty:
        return 0.0, []

    op_col = resolve_column(wms_rows.columns, "operation_type")
    qty_col = resolve_column(wms_rows.columns, "quantity")
    quantities = pd.to_numeric(
        wms_rows[qty_col],
        errors="coerce",
    ).fillna(0.0)

    stock_effect_operations = {
        "Ajustare pozitiva",
        "Ajustare negativa",
        "Receptie",
        "Livrare",
    }
    internal_operations = {
        "Mutare",
        "Mutare intre gestiuni",
        "Incarcare Camion",
    }

    operations = wms_rows[op_col].astype(str).str.strip()
    unknown = sorted(
        {
            value
            for value in operations.unique().tolist()
            if value
            and value not in stock_effect_operations
            and value not in internal_operations
        }
    )
    if unknown:
        return None, unknown

    mask = operations.isin(stock_effect_operations)
    return float(quantities.loc[mask].sum()), []
