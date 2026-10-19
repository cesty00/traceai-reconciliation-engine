"""Read-only deterministic WME stock replay, per warehouse/product/lot."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

def number(value: Any) -> Decimal | None:
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None

def moment(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None

def replay_wme_stock(
    rows: Iterable[Mapping[str, Any]],
    *,
    opening_balances: Mapping[tuple[str, str, str], Any],
    require_lot: bool = True,
    tolerance: str = "0.001",
) -> dict[str, Any]:
    """Replay complete normalized signed WME movements, fail closed on missing scope."""
    tol = number(tolerance)
    if tol is None or tol < 0:
        raise ValueError("Invalid tolerance")
    parsed = []
    errors = []
    for i, row in enumerate(rows):
        warehouse = str(row.get("warehouse") or "").strip().upper()
        article = str(row.get("product_code") or "").strip().upper()
        lot = str(row.get("lot") or "").strip().upper()
        day = moment(row.get("date"))
        qty = number(row.get("quantity"))
        source_row = row.get("source_row")
        if (not warehouse or not article or (require_lot and not lot)
            or day is None or qty is None or not isinstance(source_row, int)
            or isinstance(source_row, bool) or source_row < 1):
            errors.append({"input_index": i, "reason": "UNRESOLVED_MOVEMENT_SCOPE"})
            continue
        parsed.append((day, source_row, (warehouse, article, lot), qty, row))
    if errors:
        return {"status": "BLOCKED_WITH_REASON", "verdict": "REVIEW", "errors": errors, "timeline": []}
    opening = {}
    for key in {entry[2] for entry in parsed}:
        bal = number(opening_balances.get(key))
        if bal is None:
            errors.append({"scope": key, "reason": "MISSING_OPENING_BALANCE"})
        else:
            opening[key] = bal
    if errors:
        return {"status": "BLOCKED_WITH_REASON", "verdict": "REVIEW", "errors": errors, "timeline": []}
    seen = set()
    ledger = dict(opening)
    timeline = []
    for day, source_row, key, qty, row in sorted(parsed, key=lambda entry: (entry[0], entry[1])):
        if source_row in seen:
            return {"status": "BLOCKED_WITH_REASON", "verdict": "REVIEW",
                    "errors": [{"source_row": source_row, "reason": "DUPLICATE_SOURCE_ROW"}], "timeline": []}
        seen.add(source_row)
        before = ledger[key]
        after = before + qty
        ledger[key] = after
        observed = number(row.get("observed_balance"))
        delta = observed - after if observed is not None else None
        timeline.append({
            "date": day.isoformat(), "source_row": source_row,
            "warehouse": key[0], "product_code": key[1], "lot": key[2],
            "document": row.get("document"), "operation_type": row.get("operation_type"),
            "before": str(before), "movement": str(qty), "after": str(after),
            "observed_balance": str(observed) if observed is not None else None,
            "observed_delta": str(delta) if delta is not None else None,
            "status": "WME_BALANCE_DIFFERENCE_REVIEW" if delta is not None and abs(delta) > tol
                      else "ARITHMETIC_REPLAY_REVIEW",
        })
    return {
        "status": "REPLAY_COMPLETE_REVIEW", "verdict": "REVIEW",
        "timeline": timeline,
        "closing_balances": [
            {"warehouse": key[0], "product_code": key[1], "lot": key[2], "balance": str(balance)}
            for key, balance in sorted(ledger.items())
        ],
        "note": "Arithmetic WME replay only; neither physical count nor verified WMS equivalence.",
    }
