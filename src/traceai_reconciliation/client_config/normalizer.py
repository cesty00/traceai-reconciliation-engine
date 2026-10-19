"""TRACEAI-EXT-003: read-only, strict normalization of already-parsed source rows.

No file IO, implicit quantity sign changes, unit conversions or automatic matches.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping
from .contract import ClientProfile


def normalize_rows(profile: ClientProfile, source_key: str,
                   rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    source = next((s for s in profile.sources if s.key == source_key), None)
    if source is None:
        raise ValueError("Unknown source_key")
    required = ("product_code", "quantity", "document", "warehouse")
    if any(k not in source.columns for k in required):
        raise ValueError("Required canonical columns not mapped")
    normalized: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            rejected.append({"source_row": index, "reason": "NOT_A_MAPPING"})
            continue
        if any(source.columns[k] not in row for k in required):
            rejected.append({"source_row": index, "reason": "MISSING_SOURCE_COLUMN"})
            continue
        values = {key: row.get(column) for key, column in source.columns.items()}
        if any(values[k] is None or not str(values[k]).strip() for k in ("product_code", "document", "warehouse")):
            rejected.append({"source_row": index, "reason": "MISSING_IDENTITY"})
            continue
        try:
            quantity = Decimal(str(values["quantity"]).strip())
        except (InvalidOperation, ValueError, TypeError):
            rejected.append({"source_row": index, "reason": "INVALID_QUANTITY"})
            continue
        if not quantity.is_finite():
            rejected.append({"source_row": index, "reason": "INVALID_QUANTITY"})
            continue
        operation = values.get("operation_type")
        if operation is not None:
            operation_name = str(operation).strip().upper()
            if operation_name not in profile.operation_map:
                rejected.append({"source_row": index, "reason": "UNMAPPED_OPERATION"})
                continue
            values["operation_type"] = profile.operation_map[operation_name]
        warehouse = str(values["warehouse"]).strip().upper()
        values["warehouse"] = profile.warehouse_aliases.get(warehouse, warehouse)
        values.update({
            "product_code": str(values["product_code"]).strip(),
            "document": str(values["document"]).strip(),
            "quantity": str(quantity),
            "source_key": source_key,
            "source_row": index,
        })
        normalized.append(values)
    return {"profile_id": profile.profile_id, "source_key": source_key,
            "status": "REVIEW" if rejected else "NORMALIZED_NOT_RECONCILED",
            "rows": normalized, "rejected": rejected,
            "matching_performed": False, "stock_changed": False}
