"""Conservative full-transfer three-leg quantity comparison, per article.

Inputs are already source-filtered candidate document lines; never proves identity.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Mapping, Sequence


def _totals(rows: Sequence[Mapping[str, Any]], *, side: str) -> dict[str, float] | None:
    result = defaultdict(float)
    for row in rows:
        key = str(row.get("product_name") or "").strip().upper()
        if not key or not isinstance(row.get("source_row"), int):
            return None
        try:
            amount = float(row["quantity"])
        except (TypeError, ValueError, KeyError):
            return None
        if side == "wms":
            result[key] += abs(amount)
        elif side == "dp":
            if amount >= 0:
                return None
            result[key] += -amount
        else:
            if amount <= 0:
                return None
            result[key] += amount
    return dict(result)


def screen_complete_mose_transfer(
    wms_transfer_lines: Sequence[Mapping[str, Any]],
    wme_nt_outgoing_dp: Sequence[Mapping[str, Any]],
    wme_nt_incoming_mose: Sequence[Mapping[str, Any]],
    *, truncated: bool = False,
) -> dict[str, Any]:
    if not wms_transfer_lines or not wme_nt_outgoing_dp or not wme_nt_incoming_mose:
        return {"status": "TRANSFER_LEG_MISSING_REVIEW", "verdict": "REVIEW"}
    docs = {str(x.get("document") or "").strip() for x in wms_transfer_lines}
    nt_docs = {str(x.get("document") or "").strip() for x in
               (*wme_nt_outgoing_dp, *wme_nt_incoming_mose)}
    if len(docs) != 1 or len(nt_docs) != 1 or "" in docs | nt_docs:
        return {"status": "TRANSFER_DOCUMENT_AMBIGUOUS_REVIEW", "verdict": "REVIEW"}
    wms = _totals(wms_transfer_lines, side="wms")
    dp = _totals(wme_nt_outgoing_dp, side="dp")
    mose = _totals(wme_nt_incoming_mose, side="mose")
    if any(x is None for x in (wms, dp, mose)):
        return {"status": "TRANSFER_SOURCE_INCOMPLETE_REVIEW", "verdict": "REVIEW"}
    items = [{
        "product_name": item, "wms_outgoing": wms.get(item, 0.0),
        "wme_dp_outgoing": dp.get(item, 0.0), "wme_mose_incoming": mose.get(item, 0.0),
        "quantities_equal": abs(wms.get(item, 0)-dp.get(item, 0)) <= 1e-6
                            and abs(dp.get(item, 0)-mose.get(item, 0)) <= 1e-6,
    } for item in sorted(wms.keys() | dp.keys() | mose.keys())]
    equal = all(x["quantities_equal"] for x in items)
    return {
        "status": ("TRANSFER_SCREEN_TRUNCATED_REVIEW" if truncated else
                   "TRANSFER_QUANTITIES_EQUAL_UNVERIFIED" if equal else
                   "TRANSFER_QUANTITIES_DIFFER_REVIEW"),
        "wms_document_candidate": next(iter(docs)),
        "wme_nt_document_candidate": next(iter(nt_docs)),
        "items": items, "article_count": len(items),
        "wms_total": round(sum(wms.values()), 6),
        "wme_dp_total": round(sum(dp.values()), 6),
        "wme_mose_total": round(sum(mose.values()), 6),
        "document_identity": "NOT_VERIFIED",
        "verdict": "REVIEW", "automatic_match_allowed": False,
        "automatic_correction_allowed": False,
    }
