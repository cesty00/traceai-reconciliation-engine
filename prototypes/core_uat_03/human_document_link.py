"""Isolated human document-link validation contract; not wired to CORE/UI."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json

DECISIONS = {"CONFIRMED", "REJECTED", "INSUFFICIENT"}

def stage_document_link_decision(candidate, decision, prior_events=()):
    """Produce a new append-only *proposal*, never write or approve economics."""
    if decision.get("decision") not in DECISIONS:
        raise ValueError("invalid decision")
    required = ("case_id", "wme_document", "wms_documents", "evidence_scope")
    if any(not candidate.get(k) for k in required):
        raise ValueError("incomplete candidate")
    fields = ("reviewer", "reviewed_at", "comment", "supporting_documents",
              "people_checked", "stock_scope_checked")
    if any(not decision.get(k) for k in fields):
        raise ValueError("incomplete review")
    if not isinstance(candidate["wms_documents"], list) or not isinstance(decision["supporting_documents"], list):
        raise ValueError("invalid documents")
    if not isinstance(decision["people_checked"], list):
        raise ValueError("invalid persons")
    if not all(isinstance(x, dict) and x.get("role") and x.get("verification_reference") for x in decision["people_checked"]):
        raise ValueError("unverified personnel roles")
    try:
        stamp = datetime.fromisoformat(decision["reviewed_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timestamp missing timezone")
    except (ValueError, AttributeError):
        raise ValueError("invalid review time")
    if decision["decision"] == "CONFIRMED" and not decision.get("evidence_verified"):
        raise ValueError("confirmation requires explicit verified evidence")
    previous = list(prior_events)
    if any(item.get("case_id") != candidate["case_id"] for item in previous):
        raise ValueError("cross-case audit history")
    entry = {
        "sequence": len(previous) + 1,
        "case_id": candidate["case_id"],
        "wme_document": candidate["wme_document"],
        "wms_documents": list(candidate["wms_documents"]),
        "evidence_scope": candidate["evidence_scope"],
        "decision": decision["decision"],
        "reviewer": decision["reviewer"],
        "reviewed_at": decision["reviewed_at"],
        "comment": decision["comment"],
        "supporting_documents": list(decision["supporting_documents"]),
        "people_checked": [dict(item) for item in decision["people_checked"]],
        "stock_scope_checked": decision["stock_scope_checked"],
        "evidence_verified": bool(decision.get("evidence_verified", False)),
        "economic_verdict": "REVIEW",
        "automatic_match_allowed": False,
        "wms_mutation_allowed": False,
        "wme_mutation_allowed": False,
    }
    previous_hash = previous[-1].get("entry_hash", "") if previous else ""
    entry["previous_hash"] = previous_hash
    entry["entry_hash"] = sha256(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"proposed_event": entry, "audit_append_required": True,
            "persistence_performed": False, "human_link_status": "DOCUMENT_LINK_CONFIRMED" if entry["decision"]=="CONFIRMED" else "HUMAN_VALIDATION_PENDING",
            "economic_verdict": "REVIEW"}
