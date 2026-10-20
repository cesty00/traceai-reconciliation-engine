"""CORE-UAT-03F isolated bridge: exact source provenance, never economic MATCH.

Explicit paths, SHA and physical pointers are supplied by trusted calling code.
No CORE imports, database access, source mutation or implicit document lookup.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
from typing import Any, Mapping

def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("core_uat_03f_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def verify_evidence_pointer(pointer: Mapping[str, Any]) -> dict[str, Any]:
    kind = pointer.get("source_type")
    if kind not in ("WMS_CSV", "WME_XLSX"):
        return {"provenance_status": "REVIEW", "reason": "UNSUPPORTED_SOURCE"}
    if not pointer.get("document_ref") or not pointer.get("product_ref"):
        return {"provenance_status": "REVIEW", "reason": "MISSING_BUSINESS_IDENTITY"}
    try:
        if kind == "WMS_CSV":
            fields = pointer["expected_fields"]
            if not isinstance(fields, dict) or not {"Document", "Cod articol"}.issubset(fields):
                return {"provenance_status": "REVIEW", "reason": "MISSING_BUSINESS_COLUMNS"}
            if str(fields["Document"]) != str(pointer["document_ref"]) or str(fields["Cod articol"]) != str(pointer["product_ref"]):
                return {"provenance_status": "REVIEW", "reason": "BUSINESS_IDENTITY_CONFLICT"}
            result = _load("source_evidence").verify_wms_csv_evidence(
                pointer["source_path"], expected_sha256=pointer["source_sha256"],
                physical_row=pointer["physical_row"], expected_fields=fields,
                delimiter=pointer.get("delimiter", ";"),
                encoding=pointer.get("encoding", "utf-8-sig"))
        else:
            cells = pointer["expected_cells"]
            doc_cell = pointer["document_cell"]
            product_cell = pointer["product_cell"]
            if not isinstance(cells, dict) or not doc_cell or not product_cell or doc_cell not in cells or product_cell not in cells:
                return {"provenance_status": "REVIEW", "reason": "MISSING_BUSINESS_CELLS"}
            if str(cells[doc_cell]) != str(pointer["document_ref"]) or str(cells[product_cell]) != str(pointer["product_ref"]):
                return {"provenance_status": "REVIEW", "reason": "BUSINESS_IDENTITY_CONFLICT"}
            result = _load("wme_xlsx_evidence").verify_wme_xlsx_evidence(
                pointer["source_path"], expected_sha256=pointer["source_sha256"],
                worksheet_path=pointer["worksheet_path"],
                physical_row=pointer["physical_row"], expected_cells=cells)
    except (KeyError, TypeError, ValueError, OSError):
        return {"provenance_status": "REVIEW", "reason": "INVALID_POINTER"}
    return {
        "provenance_status": "SOURCE_ROW_VERIFIED" if result.get("verified") is True else "REVIEW",
        "reason": result.get("reason", "UNVERIFIED"),
        "source_type": kind,
        "document_ref": str(pointer["document_ref"]),
        "product_ref": str(pointer["product_ref"]),
        "physical_row": pointer["physical_row"],
        "economic_match_authorized": False,
        "adjustment_authorized": False,
        "operator_validated": False,
    }
