"""CORE-UAT-03I — combined synthetic pointer-contract and source proof gate.

No SQL index dependency and no CORE production integration.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
from typing import Any, Mapping


def _load(module_name: str):
    path = Path(__file__).with_name(module_name + ".py")
    spec = importlib.util.spec_from_file_location("uat03i_" + module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_contract_and_source(pointer: Mapping[str, Any]) -> dict[str, Any]:
    violations = _load("index_pointer_contract").validate_index_pointer_contract(pointer)
    if violations:
        return {"status": "REVIEW", "reason": "POINTER_CONTRACT_FAILED",
                "violations": list(violations), "economic_match_authorized": False,
                "adjustment_authorized": False}
    evidence = _load("source_bridge").verify_evidence_pointer(pointer)
    if evidence.get("provenance_status") != "SOURCE_ROW_VERIFIED":
        return {"status": "REVIEW", "reason": evidence.get("reason", "SOURCE_UNVERIFIED"),
                "economic_match_authorized": False, "adjustment_authorized": False}
    return {"status": "SOURCE_ROW_VERIFIED", "reason": "SOURCE_ROW_VERIFIED",
            "source_type": evidence["source_type"],
            "document_ref": evidence["document_ref"],
            "product_ref": evidence["product_ref"],
            "physical_row": evidence["physical_row"],
            "economic_match_authorized": False, "adjustment_authorized": False}
