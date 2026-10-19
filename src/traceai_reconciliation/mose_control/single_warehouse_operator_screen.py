"""Neutral review queue entries for single-warehouse DP invoices posted by MOSE user."""
from collections import defaultdict

def mose_user_dp_invoice_reviews(events):
    groups=defaultdict(list)
    for row in events:
        if str(row.get("operation_type","")).strip().upper()!="F":
            continue
        key=(str(row.get("document","")).strip(),str(row.get("date","")).strip(),str(row.get("partner","")).strip().upper())
        groups[key].append(row)
    findings=[]
    for (doc,day,partner),rows in groups.items():
        if not doc or not day or not partner:
            continue
        outgoing=[r for r in rows if isinstance(r.get("quantity"),(int,float)) and r["quantity"]<0]
        if not outgoing:
            continue
        warehouses={str(r.get("warehouse","")).strip().upper() for r in outgoing}
        users={str(r.get("user","")).strip().upper() for r in outgoing}
        if warehouses not in ({"DEPOZIT PRINCIPAL"},{"DP"}) or "MOSE" not in users:
            continue
        source_rows=[r["source_row"] for r in outgoing if isinstance(r.get("source_row"),int)]
        if len(source_rows)!=len(outgoing):
            continue
        findings.append({"status":"MOSE_USER_DIRECT_DP_INVOICE_WMS_CHECK_REVIEW",
            "invoice_document":doc,"date":day,"partner":partner,
            "warehouses":sorted(warehouses),"source_rows":sorted(set(source_rows)),
            "warning":"Neutral control: inspect WMS customer delivery; this is not a WME posting error.",
            "verdict":"REVIEW"})
    return findings
