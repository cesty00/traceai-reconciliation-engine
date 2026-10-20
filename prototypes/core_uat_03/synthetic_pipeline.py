"""CORE-UAT-03G isolated demonstration: synthetic source -> evidence -> display -> DOCX.

This is NOT integration with SQLiteSourceIndex. No existing CORE file modified.
"""
from __future__ import annotations
from pathlib import Path
from typing import Mapping, Any
import importlib.util


def _module(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("core_uat_03g_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_verified_case(
    pointer: Mapping[str, Any],
    automatic: Mapping[str, Any],
    destination: str | Path,
) -> dict[str, Any]:
    """Read-only demonstration, fail closed if source is not verified.

    The caller must supply source pointer and automatic findings explicitly.
    """
    bridge = _module("source_bridge")
    result = bridge.verify_evidence_pointer(pointer)
    if result.get("provenance_status") != "SOURCE_ROW_VERIFIED":
        return {"status": "REVIEW", "reason": result.get("reason"), "docx": None}
    if str(pointer["product_ref"]) != str(automatic.get("product_code")):
        return {"status": "REVIEW", "reason": "PRODUCT_CONFLICT", "docx": None}
    if automatic.get("economic_verdict") not in (None, "REVIEW", "NOT_MATCH"):
        return {"status": "REVIEW", "reason": "ECONOMIC_VERDICT_UNSUPPORTED", "docx": None}

    display_input = dict(automatic)
    display_input["evidence"] = [{
        "document_ref": result["document_ref"],
        "physical_row": result["physical_row"],
        "source_hash": str(pointer["source_sha256"]),
    }]
    display_input["wms_mutation_allowed"] = False
    display_input["wme_mutation_allowed"] = False
    display = _module("operator_display").build_operator_display(display_input)
    # This is a presentation artefact, not source-backed mathematical attribution.
    display["attribution_status"] = "REVIEW"
    docx = _module("docx_annex").render_validation_annex(display, destination)
    return {
        "status": "SOURCE_ROW_VERIFIED",
        "attribution_status": "REVIEW",
        "docx": str(docx),
        "economic_match_authorized": False,
        "adjustment_authorized": False,
    }
