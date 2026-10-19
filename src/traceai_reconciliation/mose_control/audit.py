"""Read-only, conservative MOSE invoice-flow diagnostics.

Inputs are normalized event dictionaries, not mutable warehouse transactions.
This module does not claim invoice-to-delivery MATCH without an explicit link.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class MoseAuditResult:
    findings: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    scope: str = "MOSE_CONTROL"
    version: str = "0.1"


def _text(value: Any) -> str:
    return str(value or "").strip().upper()


def _identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: row.get(key)
        for key in ("system", "document", "order", "product_code", "date", "warehouse", "actor", "source_row", "quantity")
        if key in row
    }


def audit_mose_flows(
    wme_events: Iterable[Mapping[str, Any]],
    wms_events: Iterable[Mapping[str, Any]],
    *,
    mose_username: str = "MOSE",
    mose_warehouse: str = "MOSE",
    principal_warehouse: str = "DEPOZIT PRINCIPAL",
) -> MoseAuditResult:
    """Return evidence candidates and review prompts, never an automatic MATCH.

    An operator's identity and a warehouse identity are independent scopes.
    Invoice F does not substitute NT. Customer name is not a warehouse.
    Absence from supplied event slices is not proof of absence in either system.
    """
    user = _text(mose_username)
    warehouse = _text(mose_warehouse)
    principal = _text(principal_warehouse)
    wme = list(wme_events)
    wms = list(wms_events)
    findings: list[dict[str, Any]] = []

    for entry in wme:
        actor = entry.get("actor")
        username = actor.get("user") if isinstance(actor, Mapping) else None
        entry_warehouse = _text(entry.get("warehouse"))
        by_user = _text(username) == user
        in_warehouse = entry_warehouse == warehouse
        if not (by_user or in_warehouse):
            continue
        operation = _text(entry.get("operation_type"))
        if operation != "F":
            continue
        product = _text(entry.get("product_code"))
        related_wms = [
            _identity(candidate)
            for candidate in wms
            if _text(candidate.get("product_code")) == product
            and product
            and _text(candidate.get("operation_type")) in ("LIVRARE", "DELIVERY")
        ]
        related_nt = [
            _identity(candidate)
            for candidate in wme
            if _text(candidate.get("operation_type")) == "NT"
            and _text(candidate.get("product_code")) == product
            and product
            and (
                _text(candidate.get("warehouse")) in (warehouse, principal)
                or _text(candidate.get("counterpart")) in (warehouse, principal)
            )
        ]
        transfer_candidates = [
            candidate for candidate in related_wms
            if _text(candidate.get("document")).startswith("TRANSFER_MOSE")
            or _text(candidate.get("order")).startswith("TRANSFER_MOSE")
        ]
        direct_candidates = [
            candidate for candidate in related_wms
            if candidate not in transfer_candidates
        ]
        if entry_warehouse == warehouse:
            status = "MOSE_F_INVOICE_REVIEW"
        elif entry_warehouse == principal and related_nt and transfer_candidates:
            status = "WAREHOUSE_CONFLICT_REVIEW"
        elif entry_warehouse == principal:
            status = "DIRECT_DELIVERY_REVIEW"
        else:
            status = "OTHER_WAREHOUSE_F_REVIEW"
        if status == "WAREHOUSE_CONFLICT_REVIEW":
            recommendation = ("A (preferata): verificati stornarea/corectarea facturii si refacturarea din MOSE. "
                              "B (avarie): analizati un NT invers doar dupa justificare si aprobare umana; "
                              "transmiterea facturii la ANAF nu interzice automat corectarea fiscala.")
        elif status == "DIRECT_DELIVERY_REVIEW":
            recommendation = ("Livrarea directa din Depozit Principal este acceptata fara TRANSFER_MOSE/NT "
                              "cand corespondenta factura F - livrare WMS este demonstrata; verificati documentele.")
        elif status == "MOSE_F_INVOICE_REVIEW":
            recommendation = "Verificati separat TRANSFER_MOSE WMS si NT WME; factura F nu inlocuieste NT."
        else:
            recommendation = "Verificati gestiunea efectiva si documentele sursa."
        findings.append({
            "status": status,
            "recommendation": recommendation,
            "policy_version": "MOSE-OP-2026-10-19",
            "verdict": "REVIEW",
            "scope": {"user_mose": by_user, "warehouse_mose": in_warehouse},
            "invoice": _identity(entry),
            "nt_candidates": related_nt,
            "wms_transfer_candidates": transfer_candidates,
            "wms_delivery_candidates": direct_candidates,
            "limitations": "Candidați doar după articol; verifică document, cantitate, dată, gestiune și trasabilitate înainte de MATCH. Sursele pot fi parțiale.",
        })
    return MoseAuditResult(findings=tuple(findings))
