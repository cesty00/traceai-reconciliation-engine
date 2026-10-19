"""Human-review case record; never translates operator approval into engine MATCH."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class MoseHumanReviewCase:
    case_id: str
    invoice: str
    product: str
    candidate_excess_outflow_kg: str
    wme_source_rows: tuple[int, ...]
    diagnosis: str = "REVIEW — posibila dubla iesire scriptica de 10 kg"
    engine_verdict: str = "REVIEW"
    operator_status: str = "AWAITING_DOCUMENT_CHECK"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["required_documents"] = [
            "Factura fiscala originala F 91655 si cantitatea real facturata pentru articol",
            "Detaliul documentului WME F 91655 si gestiunile fiecarei linii",
            "NT WME 62513, cu ambele sensuri si cantitatile",
            "TRANSFER_MOSE-202520832 in WMS, inclusiv destinatia",
            "Documentul de livrare efectiva catre client si dovada de expeditie",
        ]
        result["decision_rule"] = (
            "Operatorul compara documentele originale. Nu se confirma eroarea, "
            "nu se emite storno/NT invers si nu se marcheaza MATCH automat."
        )
        return result

def f91655_review_case() -> MoseHumanReviewCase:
    return MoseHumanReviewCase(
        case_id="MOSE-F91655-20260311",
        invoice="91655",
        product="FILE CRAP CU PIELE 300-500G, BAX 10KG VRAC",
        candidate_excess_outflow_kg="10",
        wme_source_rows=(71944, 72103),
    )
