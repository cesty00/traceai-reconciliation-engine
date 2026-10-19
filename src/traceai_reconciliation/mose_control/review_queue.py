"""Create a review queue from defensible MOSE exception findings.

Read-only case templates. Engine verdict and operator decision are independent.
No match confirmation, stock adjustments or document writes.
"""
from __future__ import annotations
from hashlib import sha256
from typing import Any, Iterable, Mapping


def _value(v: Any) -> str:
    return str(v if v is not None else "").strip()


def build_mose_review_queue(findings: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return deterministic operator cases; reject findings without source proof."""
    result: list[dict[str, Any]] = []
    for finding in findings:
        status = _value(finding.get("status"))
        if not status or status in ("REPLAY_COMPLETE_REVIEW", "ARITHMETIC_REPLAY_REVIEW"):
            continue
        invoice = finding.get("invoice")
        if not isinstance(invoice, Mapping):
            invoice = {
                "document": finding.get("invoice_document"),
                "source_row": None,
                "warehouse": None,
            }
        document = _value(invoice.get("document"))
        rows = finding.get("source_rows")
        if rows is None:
            rows = [invoice.get("source_row")]
        if not isinstance(rows, (tuple, list)):
            rows = [rows]
        evidence_rows = sorted({int(x) for x in rows if isinstance(x, int) and not isinstance(x, bool) and x > 0})
        if not document or not evidence_rows:
            continue
        seed = document + "|" + status + "|" + ",".join(map(str, evidence_rows))
        case_id = "MOSE-" + sha256(seed.encode("utf-8")).hexdigest()[:16].upper()
        result.append({
            "case_id": case_id,
            "document": document,
            "reason": status,
            "engine_verdict": "REVIEW",
            "operator_status": "AWAITING_DOCUMENT_CHECK",
            "evidence_source_rows": evidence_rows,
            "facts": {
                "warehouses": finding.get("warehouses"),
                "invoice_warehouse": invoice.get("warehouse"),
                "quantity_by_warehouse": finding.get("quantity_by_warehouse"),
            },
            "required_checks": [
                "Factura fiscala originala si liniile/cantitatile reale",
                "Fisa magazie WME: document, utilizator, gestiune, articol, sold",
                "NT WME si transferurile WMS corespunzatoare, daca exista",
                "Livrarea WMS directa catre client, daca exista",
                "Stoc scriptic ramas in fiecare gestiune dupa facturare",
            ],
            "allowed_operator_decisions": [
                "CONFIRMED_DOCUMENTARY_ERROR",
                "REJECTED_SUSPICION",
                "NEEDS_ADDITIONAL_EVIDENCE",
            ],
            "automatic_correction_allowed": False,
            "note": "Operator approval never changes engine verdict or performs WMS/WME posting.",
        })
    return sorted(result, key=lambda entry: entry["case_id"])
