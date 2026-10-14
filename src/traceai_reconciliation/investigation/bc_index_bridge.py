"""BC row provenance bridge for indexed historical investigations."""
from copy import deepcopy
from .bc_row_link import link_bc_rows, append_verified_bc_link

def attach_bc_from_index(report, index, item_id):
    manifest = index.source_manifest()
    for system, field in (("wms", "wms_movements"), ("wme", "wme_ledger")):
        if report.source_hashes.get(field) != manifest[system]["sha256"]:
            raise ValueError("BC index source identity mismatch")
    entries = [entry for entry in report.conclusion_traceability
               if entry.get("step") == "PRODUCTION_INPUT_BC"]
    if not entries:
        return 0
    wms = index.read_wms_product(report.product_code).to_dict(orient="records")
    wme_frame, ids = index.read_wme_product(report.product_name)
    if ids != {str(item_id)}:
        raise ValueError("BC index ambiguous WME product mapping")
    wme = wme_frame.to_dict(orient="records")
    candidate = deepcopy(report)
    for entry in entries:
        link = link_bc_rows(article_code=report.product_code,
                            bc_document=entry["key"].removeprefix("BC="),
                            wme_item_id=str(item_id), wms_rows=wms,
                            wme_rows=wme, source_manifest=manifest)
        append_verified_bc_link(candidate, link)
    report.conclusion_traceability = candidate.conclusion_traceability
    return len(entries)
