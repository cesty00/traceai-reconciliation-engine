"""CORE-UAT-03H: fail-closed contract for index-to-source pointers.

No inference from SQLite rowid or WME LineNo. Pure read-only input validation.
"""
from __future__ import annotations
from typing import Any, Mapping

REQUIRED = {
    "WMS_CSV": ("source_sha256", "source_path", "physical_row", "document_ref",
                "product_ref", "expected_fields", "encoding", "delimiter"),
    "WME_XLSX": ("source_sha256", "source_path", "physical_row", "document_ref",
                 "product_ref", "expected_cells", "worksheet_path",
                 "document_cell", "product_cell"),
}

def validate_index_pointer_contract(pointer: Mapping[str, Any]) -> tuple[str, ...]:
    if not isinstance(pointer, Mapping):
        return ("INVALID_POINTER",)
    kind = pointer.get("source_type")
    if kind not in REQUIRED:
        return ("UNSUPPORTED_SOURCE",)
    errors = []
    for key in REQUIRED[kind]:
        if key not in pointer or pointer[key] in (None, ""):
            errors.append("MISSING_" + key.upper())
    if pointer.get("pointer_origin") != "RAW_PHYSICAL_COORDINATE":
        errors.append("UNVERIFIED_POINTER_ORIGIN")
    row = pointer.get("physical_row")
    if isinstance(row, bool) or not isinstance(row, int) or row < (2 if kind == "WMS_CSV" else 1):
        errors.append("INVALID_PHYSICAL_ROW")
    sha = pointer.get("source_sha256")
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
        errors.append("INVALID_SHA256")
    if kind == "WMS_CSV":
        fields = pointer.get("expected_fields")
        if not isinstance(fields, Mapping) or not {"Document", "Cod articol"}.issubset(fields):
            errors.append("MISSING_BUSINESS_FIELDS")
    else:
        cells = pointer.get("expected_cells")
        if not isinstance(cells, Mapping) or not all(
            pointer.get(key) in cells for key in ("document_cell", "product_cell")
        ):
            errors.append("MISSING_BUSINESS_CELLS")
    return tuple(errors)
