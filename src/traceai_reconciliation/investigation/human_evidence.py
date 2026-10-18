"""Explicit human attestations, strictly scoped to original source rows.

This registry never changes MATCH results or authorizes WMS/WME postings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HumanAttestation:
    evidence_id: str
    product_code: str
    system: str
    source_row: int
    source_date: str
    signed_quantity: float
    unit: str
    physical_count_confirmed: bool
    counterpart_wme_exists: bool | None
    statement: str
    provenance: str

    def as_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


def applicable_attestations(
    product_code: str,
    timeline: list[dict[str, Any]],
    attestations: list[HumanAttestation],
) -> list[dict[str, Any]]:
    """Accept only a unique exact row/date/quantity/system binding.

    The same row appearing twice, an absent row, or conflicting evidence
    cannot be promoted as validated evidence.
    """
    accepted: list[dict[str, Any]] = []
    counts: dict[tuple[str, int], int] = {}
    for att in attestations:
        if att.product_code == product_code:
            key = (att.system.upper(), att.source_row)
            counts[key] = counts.get(key, 0) + 1
    seen: set[tuple[str, int]] = set()
    for att in attestations:
        if att.product_code != product_code:
            continue
        key = (att.system.upper(), att.source_row)
        if key in seen or counts[key] != 1:
            continue
        rows = [
            row for row in timeline
            if str(row.get("system", "")).upper() == key[0]
            and str(row.get("source_row", "")) == str(key[1])
            and str(row.get("date", "")).startswith(att.source_date)
            and abs(float(row.get("quantity", 0)) - att.signed_quantity) < 0.000001
        ]
        if len(rows) != 1:
            continue
        entry = att.as_dict()
        entry["validation_status"] = "HUMAN_CONFIRMED"
        entry["matched_source_row"] = rows[0]["source_row"]
        accepted.append(entry)
        seen.add(key)
    return accepted
