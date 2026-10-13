"""Conservative WMS move / WME NT candidate discovery.

Candidate equality is not a validated warehouse mapping or a MATCH.
The caller must provide already-normalized, article-filtered movements.
"""
from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class TransferEvent:
    article: str
    day: date
    document: str
    quantity: float
    source_location: str
    destination_location: str


@dataclass(frozen=True)
class NTLeg:
    article: str
    day: date
    document: str
    warehouse: str
    signed_quantity: float


@dataclass(frozen=True)
class TransferCandidate:
    wms_document: str
    nt_document: str | None
    status: str
    reason: str


def discover_transfer_candidates(
    moves: Iterable[TransferEvent],
    nt_legs: Iterable[NTLeg],
    *,
    tolerance: float = 0.001,
) -> tuple[TransferCandidate, ...]:
    """Find possible 2-leg NT counterparts without forcing one-to-one MATCH."""
    moves = tuple(moves)
    legs = tuple(nt_legs)
    out = []
    for move in moves:
        possible = []
        nt_documents = sorted({
            leg.document for leg in legs
            if leg.article == move.article and leg.day == move.day
        })
        for doc in nt_documents:
            related = [leg for leg in legs if leg.document == doc
                       and leg.article == move.article and leg.day == move.day]
            negative = -sum(leg.signed_quantity for leg in related if leg.signed_quantity < 0)
            positive = sum(leg.signed_quantity for leg in related if leg.signed_quantity > 0)
            from_wh = {leg.warehouse for leg in related if leg.signed_quantity < 0}
            to_wh = {leg.warehouse for leg in related if leg.signed_quantity > 0}
            if (abs(negative - move.quantity) <= tolerance
                and abs(positive - move.quantity) <= tolerance
                and abs(sum(leg.signed_quantity for leg in related)) <= tolerance
                and len(from_wh) == 1 and len(to_wh) == 1
                and from_wh != to_wh):
                possible.append(doc)
        if len(possible) == 1:
            out.append(TransferCandidate(move.document, possible[0], "REVIEW",
                                         "DOCUMENTARY_CANDIDATE_SCOPE_UNVERIFIED"))
        elif possible:
            out.append(TransferCandidate(move.document, None, "REVIEW",
                                         "MULTIPLE_NT_CANDIDATES"))
        else:
            out.append(TransferCandidate(move.document, None, "REVIEW",
                                         "NO_VERIFIED_NT_CANDIDATE"))
    return tuple(out)
