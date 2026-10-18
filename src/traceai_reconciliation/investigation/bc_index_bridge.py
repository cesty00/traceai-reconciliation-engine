"""Historical BC evidence bridging with explicit review for unresolved documents."""
from copy import deepcopy
from datetime import datetime
import re

from .bc_row_link import link_bc_rows, append_verified_bc_link
from .production_matching import normalize_document


def _period_start(period):
    first = period.split("-", 1)[0].strip()
    try:
        return datetime.strptime(first, "%d.%m.%Y").date()
    except ValueError:
        return None


def _date(value):
    text = str(value or "").strip()
    for pattern in ("%m/%d/%Y %I:%M:%S %p", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _review_entry(document, reason, evidence=""):
    return {
        "step": "BC_SOURCE_REVIEW",
        "source": "Indexed WMS/WME historical sources",
        "key": f"BC={document}",
        "rule": reason,
        "result": evidence or "Source-row association not verified; human investigation required",
        "evidence_level": "D",
    }


def attach_bc_from_index(report, index, item_id):
    """Attach uniquely matching rows while retaining all exceptions as REVIEW.

    Source identity and WME item mapping are mandatory. No automatic verdict,
    human approval or quantity correction is ever created.
    """
    manifest = index.source_manifest()
    for system, field in (("wms", "wms_movements"), ("wme", "wme_ledger")):
        if report.source_hashes.get(field) != manifest[system]["sha256"]:
            raise ValueError("BC index source identity mismatch")
    entries = [item for item in report.conclusion_traceability
               if item.get("step") == "PRODUCTION_INPUT_BC"]
    if not entries:
        return 0
    wms = index.read_wms_product(report.product_code).to_dict(orient="records")
    wme_frame, ids = index.read_wme_product(report.product_name)
    if ids != {str(item_id)}:
        raise ValueError("BC index ambiguous WME product mapping")
    wme = wme_frame.to_dict(orient="records")
    candidate = deepcopy(report)
    unresolved = 0
    for entry in entries:
        document = normalize_document(entry["key"].removeprefix("BC="))
        try:
            link = link_bc_rows(
                article_code=report.product_code, bc_document=document,
                wme_item_id=str(item_id), wms_rows=wms,
                wme_rows=wme, source_manifest=manifest,
            )
        except ValueError as exc:
            if "ambiguous or missing source event" not in str(exc):
                raise
            candidate.conclusion_traceability.append(
                _review_entry(document, "BC_SOURCE_MISSING_OR_AMBIGUOUS")
            )
            unresolved += 1
            continue
        if link["status"] == "QTY_EQUAL":
            # An equal historical pair may cross the reconciliation start date.
            # Make this explicitly visible without treating it as an in-period MATCH.
            wms_original = next(
                row for row in wms if row.get("SourceRowNumber") == link["wms_row"]
            )
            wme_original = next(
                row for row in wme if row.get("SourceRowNumber") == link["wme_row"]
            )
            start = _period_start(report.period)
            wdate = _date(wms_original.get("Data"))
            edate = _date(wme_original.get("Date"))
            crossing = bool(start and wdate and edate and wdate < start <= edate)
            candidate.conclusion_traceability.append(_review_entry(
                document,
                "BC_CROSS_PERIOD_REVIEW" if crossing else "BC_CALCULATION_SCOPE_REVIEW",
                f"WMS_ROW={link['wms_row']} DATE={wdate} QTY={link['wms_qty']}; "
                f"WME_ROW={link['wme_row']} DATE={edate} QTY={link['wme_qty']}; "
                "historical row equality is not in-period economic MATCH",
            ))
            unresolved += 1
            continue
        try:
            append_verified_bc_link(candidate, link)
        except ValueError as exc:
            if "contradict calculated report discrepancy" not in str(exc):
                raise
            candidate.conclusion_traceability.append(
                _review_entry(document, "BC_CALCULATION_SCOPE_REVIEW",
                              "Indexed rows conflict with period-filtered matcher")
            )
            unresolved += 1
    if unresolved and report.verdict == "MATCH_DIRECT":
        raise ValueError("Unresolved BC records must not be published as MATCH_DIRECT")
    report.conclusion_traceability = candidate.conclusion_traceability
    return len(entries) - unresolved
