"""CORE-UAT-04D isolated causal ownership contract; no CORE runtime usage."""
from __future__ import annotations
from collections import defaultdict
from typing import Mapping, Any

def validate_causal_ownership(components: list[Mapping[str, Any]], tolerance: float = 0.001) -> dict[str, Any]:
    """Fail closed on reused event, incomplete pointers, or arithmetic mismatch.

    A document number alone never identifies an economic event. The event's
    immutable identity includes source hash, source row, system and event key.
    """
    claimed: dict[tuple, str] = {}
    problems: list[str] = []
    summaries = []
    for component in components:
        owner = str(component.get("component_id") or "")
        events = component.get("events")
        if not owner or not isinstance(events, list) or not events:
            problems.append("EMPTY_COMPONENT_OR_EVENTS")
            continue
        seen_local = set()
        amount = 0.0
        for e in events:
            if not isinstance(e, Mapping):
                problems.append("INVALID_EVENT")
                continue
            keys = ("system", "source_sha256", "physical_row", "event_key", "document")
            if any(not e.get(k) for k in keys):
                problems.append("MISSING_EVENT_POINTER")
                continue
            sha = e["source_sha256"]
            if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha):
                problems.append("INVALID_SOURCE_SHA")
                continue
            if not isinstance(e["physical_row"], int) or isinstance(e["physical_row"], bool) or e["physical_row"] <= 0:
                problems.append("INVALID_SOURCE_ROW")
                continue
            identity = (str(e["system"]), sha.lower(), e["physical_row"], str(e["event_key"]))
            if identity in seen_local:
                problems.append("DUPLICATE_EVENT_WITHIN_COMPONENT")
                continue
            seen_local.add(identity)
            if identity in claimed:
                problems.append("DOUBLE_COUNTED_EVENT")
                continue
            claimed[identity] = owner
            try:
                if isinstance(e.get("effect"), bool):
                    raise ValueError("boolean quantity")
                amount += float(e["effect"])
            except (KeyError, ValueError, TypeError):
                problems.append("INVALID_EVENT_EFFECT")
        expected = component.get("effect")
        try:
            if expected is None or isinstance(expected, bool) or abs(amount - float(expected)) > tolerance:
                problems.append("COMPONENT_EFFECT_MISMATCH")
        except (TypeError, ValueError):
            problems.append("COMPONENT_EFFECT_MISMATCH")
        summaries.append({"component_id": owner, "event_count": len(seen_local), "calculated_effect": round(amount, 6)})
    return {"status": "REVIEW" if problems else "OWNERSHIP_VERIFIED",
            "problems": sorted(set(problems)), "components": summaries,
            "economic_match_authorized": False, "adjustment_authorized": False}
