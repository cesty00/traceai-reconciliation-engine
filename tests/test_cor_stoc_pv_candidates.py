"""Regression guards based on documented article 10002 PV cases.

These are reduced documentary fixtures, not an original-source E2E run.
"""
from traceai_reconciliation.investigation.cor_stoc_pv_candidates import find_cor_stoc_pv_candidates


def test_pv2676_explicit_rows_do_not_silently_absorb_unreferenced_line():
    wms = [
        {"Cod-motiv": "COR STOC", "Detalii": "PV 2676", "Cantitate": -450, "SourceRowNumber": 274987},
        {"Cod-motiv": "COR STOC", "Detalii": "PV 2676", "Cantitate": -145, "SourceRowNumber": 274986},
        {"Cod-motiv": "COR STOC", "Detalii": "corectie stoc", "Cantitate": -450, "SourceRowNumber": 274988},
    ]
    wme = [
        {"OperationType": "PV", "Document": "PV 2676", "SignedQuantity": -856.9999, "SourceRowNumber": 48064},
        {"OperationType": "PV", "Document": "PV 2676", "SignedQuantity": -188.0001, "SourceRowNumber": 48065},
    ]
    result = find_cor_stoc_pv_candidates(wms, wme)
    assert len(result) == 1
    assert result[0]["explicit_wms_quantity"] == -595
    assert result[0]["pv_quantity"] == -1045
    assert not result[0]["quantity_equal_explicit_rows"]
    assert result[0]["economic_match"] is False
    assert result[0]["status"] == "COR_STOC_PV_SOURCE_REVIEW"


def test_pv2552_without_explicit_reference_is_not_invented():
    wms = [{"Cod-motiv": "COR STOC", "Detalii": "regularizare", "Cantitate": -350}]
    wme = [{"OperationType": "PV", "Document": "PV 2552", "SignedQuantity": -350}]
    assert find_cor_stoc_pv_candidates(wms, wme) == []


def test_pv2265_netting_must_not_be_assumed_from_one_explicit_row():
    wms = [
        {"Cod-motiv": "COR STOC", "Detalii": "PV 2265", "Cantitate": -900},
        {"Cod-motiv": "COR STOC", "Detalii": "regularizare", "Cantitate": 450},
    ]
    wme = [{"OperationType": "PV", "Document": "PV 2265", "SignedQuantity": -450}]
    result = find_cor_stoc_pv_candidates(wms, wme)
    assert len(result) == 1
    assert result[0]["explicit_wms_quantity"] == -900
    assert result[0]["economic_match"] is False


def test_equal_quantity_different_document_does_not_match():
    wms = [{"Cod-motiv": "COR STOC", "Detalii": "PV 9999", "Cantitate": -450}]
    wme = [{"OperationType": "PV", "Document": "PV 2265", "SignedQuantity": -450}]
    assert find_cor_stoc_pv_candidates(wms, wme) == []
