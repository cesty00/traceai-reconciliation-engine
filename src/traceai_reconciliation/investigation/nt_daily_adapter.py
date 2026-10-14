"""Fail-closed adapter from indexed daily source rows to NT candidate discovery."""
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from math import isfinite

from .nt_transfer_candidates import NTLeg, TransferEvent, discover_transfer_candidates


def _day(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw)[:19].replace("Z", "")).date()
    except ValueError:
        return None


def _number(raw):
    try:
        value = float(raw)
        return value if isfinite(value) else None
    except (ValueError, TypeError):
        return None


def analyze_nt_candidates_in_window(window):
    """Diagnostic only. Missing fields or competing events block attribution.

    No global warehouse correspondence or causal stock effect is inferred.
    """
    grouped = defaultdict(list)
    warnings = []
    for i, row in enumerate(window.wms_rows):
        operation = str(row.get("Tip operatiune") or row.get("operation_type") or "").casefold()
        if operation not in ("mutare intre gestiuni", "mutare între gestiuni", "mutare"):
            continue
        day = _day(row.get("Data") or row.get("date"))
        doc = str(row.get("Numar comanda") or row.get("Document") or "").strip()
        src = str(row.get("Locatie sursa") or "").strip()
        dst = str(row.get("Locatie destinatie") or "").strip()
        qty = _number(row.get("Cantitate"))
        if not day or not doc or not src or not dst or src == dst or qty is None or qty == 0:
            warnings.append({"wms_row": i, "reason": "WMS_MOVE_METADATA_INCOMPLETE"})
            continue
        grouped[(day, doc, src, dst)].append(abs(qty))
    moves = [
        TransferEvent(window.product_code,day,doc,sum(qs),src,dst)
        for (day,doc,src,dst),qs in sorted(grouped.items())
    ]
    legs = []
    for i, row in enumerate(window.wme_rows):
        if str(row.get("OperationType") or "").upper().strip() != "NT":
            continue
        day = _day(row.get("Date") or row.get("Data"))
        doc = str(row.get("Document") or "").strip()
        wh = str(row.get("Warehouse") or "").strip()
        qty = _number(row.get("SignedQuantity"))
        if not day or not doc or not wh or qty is None or qty == 0:
            warnings.append({"wme_row": i, "reason": "NT_METADATA_INCOMPLETE"})
            continue
        legs.append(NTLeg(window.product_code, day, doc, wh, qty))
    candidates = list(discover_transfer_candidates(moves, legs))
    # A single NT must never be allocated to several WMS moves.
    counts = defaultdict(int)
    for candidate in candidates:
        if candidate.nt_document:
            counts[candidate.nt_document] += 1
    return {
        "status": "REVIEW",
        "candidates": [
            dict(asdict(candidate),
                 **({"nt_document": None, "reason": "SHARED_NT_CANDIDATE"}
                    if candidate.nt_document and counts[candidate.nt_document] > 1 else {}))
            for candidate in candidates
        ],
        "warnings": warnings,
        "scope_verified": False,
    }
