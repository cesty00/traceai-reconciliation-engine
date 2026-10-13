from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .delta_movement_window import DeltaMovementWindowResult
from .source_readers import resolve_column


@dataclass(frozen=True, slots=True)
class DeltaEvidenceItem:
    source: str
    quantity: float
    difference_effect: float
    document: str | None
    operation_type: str | None
    operation_date: str | None


@dataclass(frozen=True, slots=True)
class DeltaRootCauseResult:
    product_code: str
    previous_difference: float
    current_difference: float
    observed_delta: float
    explained_delta: float
    residual_delta: float
    status: str
    evidence: tuple[DeltaEvidenceItem, ...]
    note: str


def _value(record: dict[str, Any], semantic: str) -> Any:
    column = resolve_column(record.keys(), semantic, required=False)
    if column is None:
        return None
    return record.get(column)


def _signed_quantity(record: dict[str, Any]) -> float:
    value = _value(record, "quantity")
    if value is None:
        raise ValueError(
            "Delta root cause cannot resolve a signed quantity column."
        )
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        raise ValueError(
            f"Delta root cause found an invalid signed quantity: {value!r}"
        )
    return float(numeric)


def _evidence_from_record(
    source: str,
    record: dict[str, Any],
) -> DeltaEvidenceItem:
    quantity = _signed_quantity(record)

    # Stock-report difference is WMS - WME.
    # Therefore a signed WMS movement changes the difference by +q,
    # while the equivalent WME movement changes it by -q.
    if source == "WMS":
        # Internal warehouse relocations affect location balances, not the
        # aggregate physical inventory across the in-scope warehouses.
        # The event remains in evidence but must not create a stock delta.
        operation = _value(record, "operation_type")
        normalized_operation = str(operation or "").strip().casefold()
        if normalized_operation in {"mutare", "mutare intre gestiuni", "mutare între gestiuni"}:
            effect = 0.0
        else:
            effect = quantity
    elif source == "WME":
        effect = -quantity
    else:
        raise ValueError(f"Unsupported arithmetic delta source: {source}")

    document = _value(record, "document")
    operation_type = _value(record, "operation_type")
    operation_date = _value(record, "date")

    return DeltaEvidenceItem(
        source=source,
        quantity=quantity,
        difference_effect=effect,
        document=(
            str(document).strip()
            if document is not None and str(document).strip()
            else None
        ),
        operation_type=(
            str(operation_type).strip()
            if operation_type is not None and str(operation_type).strip()
            else None
        ),
        operation_date=(
            str(operation_date).strip()
            if operation_date is not None and str(operation_date).strip()
            else None
        ),
    )


def analyze_delta_root_cause(
    *,
    movement_window: DeltaMovementWindowResult,
    previous_difference: float,
    current_difference: float,
    tolerance: float = 1e-6,
    stock_scope: str | None = None,
) -> DeltaRootCauseResult:
    """Explain a stock-difference change from new WMS/WME movements only.

    Production rows are retained by the movement window as contextual evidence
    but are intentionally excluded from arithmetic explanation here because
    production may already be represented through WMS/WME stock movements.
    Counting them again would risk double counting.

    The analyzer is conservative:
    - EXACT_EVENT: exactly one WMS/WME movement explains the observed delta.
    - MULTI_EVENT: all non-zero WMS/WME movements jointly explain the delta.
    - UNEXPLAINED: the candidate movements do not close the observed delta.
    """
    if stock_scope not in (None, "AGGREGATE", "WAREHOUSE"):
        raise ValueError("stock_scope must be AGGREGATE, WAREHOUSE, or None")

    previous = float(previous_difference)
    current = float(current_difference)
    observed = current - previous

    evidence = tuple(
        [
            _evidence_from_record("WMS", item)
            for item in movement_window.wms_rows
        ]
        + [
            _evidence_from_record("WME", item)
            for item in movement_window.wme_rows
        ]
    )
    internal_transfer = any(
        item.source == "WMS"
        and str(item.operation_type or "").strip().casefold()
        in {"mutare", "mutare intre gestiuni", "mutare între gestiuni"}
        for item in evidence
    )
    # Source extraction currently does not prove whether both transfer ends
    # are in scope. A single-warehouse or unknown scope must fail closed.
    if internal_transfer and stock_scope != "AGGREGATE":
        return DeltaRootCauseResult(
            product_code=movement_window.product_code,
            previous_difference=previous,
            current_difference=current,
            observed_delta=observed,
            explained_delta=0.0,
            residual_delta=observed,
            status="UNEXPLAINED",
            evidence=evidence,
            note="TRANSFER_SCOPE_UNVERIFIED: warehouse scope and transfer direction require review.",
        )

    non_zero = tuple(
        item for item in evidence if abs(item.difference_effect) > tolerance
    )
    explained = sum(item.difference_effect for item in non_zero)
    residual = observed - explained

    exact_matches = tuple(
        item
        for item in non_zero
        if abs(observed - item.difference_effect) <= tolerance
    )

    if len(non_zero) == 1 and len(exact_matches) == 1:
        status = "EXACT_EVENT"
        note = (
            "A single new WMS/WME movement explains the complete change "
            "between stock snapshots."
        )
        explained = exact_matches[0].difference_effect
        residual = observed - explained
        selected = exact_matches
    elif len(non_zero) >= 2 and abs(residual) <= tolerance:
        status = "MULTI_EVENT"
        note = (
            "All new non-zero WMS/WME movements in the snapshot window "
            "jointly explain the complete change."
        )
        selected = non_zero
    else:
        status = "UNEXPLAINED"
        note = (
            "The new WMS/WME movements do not fully explain the observed "
            "stock-difference change. No match is forced."
        )
        selected = non_zero

    return DeltaRootCauseResult(
        product_code=movement_window.product_code,
        previous_difference=previous,
        current_difference=current,
        observed_delta=observed,
        explained_delta=explained,
        residual_delta=residual,
        status=status,
        evidence=selected,
        note=note,
    )
