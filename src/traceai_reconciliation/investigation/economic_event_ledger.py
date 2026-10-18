"""Read-only canonical event ownership guard for TraceAI V1 Daily.

Does not infer MATCH or mutate WMS/WME. Events are registered only when the
caller has independent evidence supporting their economic interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

System = Literal["WMS", "WME"]


@dataclass(frozen=True)
class SourceLine:
    system: System
    source_sha256: str
    row_number: int

    def __post_init__(self) -> None:
        if not self.source_sha256 or self.row_number < 1:
            raise ValueError("SourceLine requires hash and physical row number")


@dataclass(frozen=True)
class EconomicEvent:
    event_id: str
    source_lines: tuple[SourceLine, ...]
    delta_wms_minus_wme: float
    evidence_status: Literal["CONFIRMED", "REVIEW"]
    explanation: str

    def __post_init__(self) -> None:
        if not self.event_id or not self.source_lines or not self.explanation:
            raise ValueError("Event id, source provenance and explanation required")
        if len(set(self.source_lines)) != len(self.source_lines):
            raise ValueError("Repeated source row inside economic event")
        if self.evidence_status == "REVIEW" and self.delta_wms_minus_wme != 0:
            raise ValueError("REVIEW candidates cannot claim confirmed economic impact")


class EventOwnershipLedger:
    """Deny reuse of the same physical source row by confirmed events.

    REVIEW evidence may overlap other views of the same document: it is not
    counted as confirmed impact or used to neutralize a residual.
    """

    def __init__(self) -> None:
        self._confirmed_owners: dict[SourceLine, str] = {}
        self._events: list[EconomicEvent] = []
        self._event_ids: set[str] = set()

    def register(self, event: EconomicEvent) -> None:
        if event.event_id in self._event_ids:
            raise ValueError(f"Duplicate economic event id: {event.event_id}")
        if event.evidence_status == "CONFIRMED":
            for source in event.source_lines:
                if source in self._confirmed_owners:
                    raise ValueError(
                        f"Source row already claimed by {self._confirmed_owners[source]}"
                    )
            for source in event.source_lines:
                self._confirmed_owners[source] = event.event_id
        self._events.append(event)
        self._event_ids.add(event.event_id)

    @property
    def confirmed_impact(self) -> float:
        return sum(
            e.delta_wms_minus_wme for e in self._events
            if e.evidence_status == "CONFIRMED"
        )

    @property
    def events(self) -> tuple[EconomicEvent, ...]:
        return tuple(self._events)
