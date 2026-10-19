"""Conservative invoice-posting WME balance evidence, per warehouse.

WME Balance is reported after each source movement; quantity must be signed.
This checks row-level arithmetic only, not cross-system matching or true stock.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

def _decimal(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None

def invoice_balance_evidence(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    records = []
    incomplete = []
    for index, row in enumerate(rows):
        qty = _decimal(row.get("quantity"))
        after = _decimal(row.get("reported_balance"))
        warehouse = str(row.get("warehouse") or "").strip().upper()
        unit = str(row.get("unit") or "").strip().upper()
        source = row.get("source_row")
        if (qty is None or after is None or not warehouse or not unit
                or not isinstance(source, int) or isinstance(source, bool)):
            incomplete.append(index)
            continue
        records.append({
            "warehouse": warehouse,
            "unit": unit,
            "source_row": source,
            "signed_quantity": str(qty),
            "balance_before_this_line": str(after - qty),
            "balance_after_this_line": str(after),
            "status": "ROW_ARITHMETIC_ONLY_REVIEW",
        })
    return {
        "status": "INCOMPLETE_BALANCE_EVIDENCE_REVIEW" if incomplete else "ROW_BALANCES_EXTRACTED_REVIEW",
        "verdict": "REVIEW",
        "records": records,
        "incomplete_row_indices": incomplete,
        "warning": "Before balance is inferred from this row's posted after-balance and signed quantity; not an independent WME verification. Other same-day postings and stock ownership are unverified.",
    }
