import pytest
from traceai_reconciliation.investigation.bc_row_link import link_bc_rows

MANIFEST = {
    "wms": {"file_name": "trace.csv", "sha256": "a" * 64},
    "wme": {"file_name": "ledger.xlsx", "sha256": "b" * 64},
}

@pytest.mark.parametrize("doc,wms_qty,wme_qty,wr,er,diff", [
    ("23448", -720, -90, 281807, 48162, -630),
    ("23454", -400, -50, 281823, 48161, -350),
    ("23462", -880, -110, 281841, 48159, -770),
    ("23467", -400, -50, 281842, 48160, -350),
])
def test_bc_row_identity_and_documentary_difference(doc,wms_qty,wme_qty,wr,er,diff):
    evidence = link_bc_rows(
        article_code="10002", bc_document=doc, wme_item_id="1494",
        wms_rows=[{"Cod articol":"10002", "Numar comanda":"00"+doc+"_DC",
                   "Tip operatiune":"Ajustare negativa", "Cod-motiv":"PRODUCTION-IN",
                   "SourceRowNumber":wr,"Cantitate":wms_qty}],
        wme_rows=[{"WMEItemId":"1494", "OperationType":"BC","Document":doc,
                   "SourceRowNumber":er,"SignedQuantity":wme_qty}],
        source_manifest=MANIFEST,
    )
    assert evidence["difference"]==diff
    assert evidence["status"]=="QTY_DIFF"
    assert evidence["wms_row"]==wr and evidence["wme_row"]==er
    assert evidence["human_validation"]=="NOT_ATTACHED"

def test_bc_link_rejects_wrong_item_or_ambiguous_rows():
    wms={"Cod articol":"10002","Numar comanda":"0023448_DC",
         "Tip operatiune":"Ajustare negativa","Cod-motiv":"PRODUCTION-IN",
         "SourceRowNumber":281807,"Cantitate":-720}
    wme={"WMEItemId":"9999","OperationType":"BC","Document":"23448",
         "SourceRowNumber":48162,"SignedQuantity":-90}
    params=dict(article_code="10002",bc_document="23448",wme_item_id="1494",
                wms_rows=[wms],wme_rows=[wme],source_manifest=MANIFEST)
    with pytest.raises(ValueError, match="ambiguous or missing"):
        link_bc_rows(**params)
    with pytest.raises(ValueError, match="ambiguous or missing"):
        link_bc_rows(**{**params,"wme_rows":[{**wme,"WMEItemId":"1494"}]*2})
    with pytest.raises(ValueError, match="ambiguous or missing"):
        link_bc_rows(**{**params,"wms_rows":[{**wms,"Numar comanda":"0023454_DC"}],
                               "wme_rows":[{**wme,"WMEItemId":"1494"}]})
