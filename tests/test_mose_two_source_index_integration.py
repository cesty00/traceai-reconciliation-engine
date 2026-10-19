"""MOSE-only index integration: no production export required."""
import csv

from openpyxl import Workbook
from traceai_reconciliation.mose_control.mose_source_index import MOSESQLiteSourceIndex
from traceai_reconciliation.mose_control.index_auto_review import create_review_cases_from_existing_index
from traceai_reconciliation.mose_control.dossier_from_index import dossier_from_current_index


PRODUCT = "FILE CRAP CU PIELE 300-500G, BAX 10KG VRAC"


def test_mose_build_screen_and_dossier_no_production(tmp_path):
    wms = tmp_path / "wms.csv"
    with wms.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(["Data", "Cod articol", "Denumire articol", "Numar comanda",
                         "Partener", "Tip operatiune", "Cantitate"])
        writer.writerow(["3/11/2026 12:25:11 PM", "DS099903867", PRODUCT,
                         "TRANSFER_MOSE-202520832", "DP->MOSE", "Livrare", "-10"])
    wme = tmp_path / "wme.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["column_" + str(i) for i in range(17)])
    def add_row(no, operation, doc, date, incoming, outgoing, balance, partner, warehouse, note):
        sheet.append([no, operation, doc, date, incoming, outgoing, balance,
                      19.12, "3711", partner, PRODUCT, None, 1801,
                      warehouse, "KG", note, 1])
    add_row(1, "NT", 62513, "11.03.2026", 0, 10, 6570,
            "MOSE", "DEPOZIT PRINCIPAL", "TESTREST")
    add_row(2, "F", 91655, "11.03.2026", 0, 10, 6560,
            "FISHERMEN INN S.R.L.", "DEPOZIT PRINCIPAL", "MOSE")
    add_row(3, "NT", 62513, "11.03.2026", 10, 0, 10,
            "DEPOZIT PRINCIPAL", "MOSE", "TESTREST")
    add_row(4, "F", 91655, "11.03.2026", 0, 10, 0,
            "FISHERMEN INN S.R.L.", "MOSE", "MOSE")
    workbook.save(wme)
    index = MOSESQLiteSourceIndex(tmp_path / "cache")
    assert index.ensure_mose_index(wms, wme) is True
    assert index.is_mose_current(wms, wme)
    assert index.ensure_mose_index(wms, wme) is False
    result = create_review_cases_from_existing_index(
        cache_dir=index.cache_dir, wms_path=wms, wme_path=wme)
    assert result["status"] == "WME_CROSS_WAREHOUSE_SCREEN_REVIEW"
    assert len(result["cases"]) == 1
    case = result["cases"][0]
    assert case["engine_verdict"] == "REVIEW"
    dossier = dossier_from_current_index(
        case=case, cache_dir=index.cache_dir, wms_path=wms, wme_path=wme)
    assert dossier["status"] == "AWAITING_OPERATOR_DOCUMENT_CHECK"
    assert dossier["invoice_to_delivery_link"] == "NOT_VERIFIED"
    assert len(dossier["wme_invoices_source_evidence"]) == 2
    assert len(dossier["wms_transfer_candidates_unverified"]) == 1
    assert dossier["wms_delivery_candidates_unverified"] == []
    assert dossier["automatic_correction_allowed"] is False
    assert dossier["verdict"] == "REVIEW"
    assert dossier["nt_to_wms_link"] == "NOT_VERIFIED"
    assert dossier["generic_evidence_audit"]["checks"]["INVOICE_SINGLE_WAREHOUSE"] == "SUSPECT_REVIEW"
    assert dossier["generic_evidence_audit"]["checks"]["MULTI_WAREHOUSE_F_OUTFLOW"] == "SUSPECT_REVIEW"
    assert dossier["document_link_audit"]["document_link_status"] == "NOT_VERIFIED"
    assert dossier["document_link_audit"]["customer_order_candidates"] == []
    assert dossier["quantity_candidate_audit"]["items"][0]["status"] == "NO_CUSTOMER_DELIVERY_CANDIDATE_REVIEW"
    assert dossier["quantity_candidate_audit"]["automatic_match_allowed"] is False

