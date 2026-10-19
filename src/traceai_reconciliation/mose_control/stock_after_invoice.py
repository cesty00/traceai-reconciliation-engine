"""Read-only per-warehouse WME balance checks after an invoice.

A balance check is not proof of physical stock or of WMS reconciliation.
Never synthesize MOSE warehouse quantities from WMS transfer orders.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def _decimal(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def check_invoice_stock(
    *,
    invoice: Mapping[str, Any],
    before_balance: Any,
    after_balance: Any,
    tolerance: str = "0.001",
) -> dict[str, Any]:
    """Check one WME F row and observed balance in the *same* WME warehouse.

    Caller must provide consecutive source-backed balances with warehouse,
    product and lot scope already verified. Does not infer sequence or claim
    that the balance from a different warehouse represents this invoice.
    """
    base = {
        "verdict": "REVIEW",
        "warehouse": invoice.get("warehouse"),
        "document": invoice.get("document"),
        "source_row": invoice.get("source_row"),
        "expected_after": None,
        "observed_after": None,
        "delta": None,
    }
    if (str(invoice.get("operation_type") or "").strip().upper() != "F"
            or not invoice.get("warehouse")
            or not invoice.get("product_code")
            or invoice.get("source_row") is None):
        return {**base, "status": "INCOMPLETE_INVOICE_SCOPE_REVIEW"}
    q, start, end = (_decimal(invoice.get("quantity")),
                     _decimal(before_balance), _decimal(after_balance))
    if q is None or start is None or end is None:
        return {**base, "status": "MISSING_BALANCE_EVIDENCE_REVIEW"}
    try:
        tol = Decimal(tolerance)
    except InvalidOperation as exc:
        raise ValueError("Invalid tolerance") from exc
    if not tol.is_finite() or tol < 0:
        raise ValueError("Invalid tolerance")
    expected = start + q
    delta = end - expected
    result = {
        **base,
        "expected_after": str(expected),
        "observed_after": str(end),
        "delta": str(delta),
    }
    if abs(delta) > tol:
        return {**result, "status": "WME_BALANCE_INCONSISTENCY_REVIEW"}
    return {**result, "status": "WME_BALANCE_ARITHMETIC_OK_REVIEW"}


def explain_warehouse_allocation(
    *,
    principal_before: Any,
    mose_before: Any,
    transfer_quantity: Any,
    invoice_quantity: Any,
    invoice_warehouse: str,
) -> dict[str, Any]:
    """Illustrative ledger simulation, NOT a reconstruction of actual stock.

    Transfer is positive amount DP -> MOSE, invoice quantity is positive
    outbound amount; separate from WMS, which may not hold a MOSE ledger.
    """
    values = [_decimal(x) for x in (principal_before, mose_before, transfer_quantity, invoice_quantity)]
    if any(x is None for x in values):
        return {"status": "INSUFFICIENT_QUANTITIES_REVIEW", "verdict": "REVIEW"}
    dp, mose, transfer, billed = values
    if transfer < 0 or billed < 0:
        return {"status": "INVALID_FLOW_DIRECTION_REVIEW", "verdict": "REVIEW"}
    after_transfer_dp = dp - transfer
    after_transfer_mose = mose + transfer
    name = " ".join(invoice_warehouse.strip().upper().split())
    if name == "MOSE":
        after_transfer_mose -= billed
    elif name == "DEPOZIT PRINCIPAL":
        after_transfer_dp -= billed
    else:
        return {"status": "OTHER_WAREHOUSE_REVIEW", "verdict": "REVIEW"}
    return {
        "status": "ILLUSTRATIVE_LEDGER_REVIEW",
        "verdict": "REVIEW",
        "principal_after": str(after_transfer_dp),
        "mose_after": str(after_transfer_mose),
        "total_after": str(after_transfer_dp + after_transfer_mose),
        "warning": "Simulare aritmetica; nu certifica stoc fizic, alocarea documentara sau corectii.",
    }
