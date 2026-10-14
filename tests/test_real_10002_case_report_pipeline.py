"""BC evidence must survive the actual case builder and DOCX renderer.

Uses operator-verified reference quantities, not a substitute for a full-source
Daily end-to-end test.
"""
from zipfile import ZipFile

import pandas as pd
import pytest

from traceai_reconciliation.investigation.production_input_matching import match_production_inputs
from traceai_reconciliation.investigation.models import ProductInvestigationResult
from traceai_reconciliation.investigation.case_builder import build_case_report
from traceai_reconciliation.reports import generate_docx_report


def test_four_bc_quantity_differences_remain_visible_in_report(tmp_path):
    records = [
        ("0023448_DC", -720, "23448", -90, -630, 281807, 48162),
        ("0023454_DC", -400, "23454", -50, -350, 281823, 48161),
        ("0023462_DC", -880, "23462", -110, -770, 281841, 48159),
        ("0023467_DC", -400, "23467", -50, -350, 281842, 48160),
    ]
    wms = pd.DataFrame([
        {"Tip operatiune": "Ajustare negativa", "Cod-motiv": "PRODUCTION-IN",
         "Numar comanda": order, "Cantitate": wqty, "Data": "02.01.2026",
         "Detalii": "Order production number: DECONGELARE " + order}
        for order, wqty, _, _, _, _, _ in records
    ])
    wme = pd.DataFrame([
        {"OperationType": "BC", "Document": doc, "SignedQuantity": eqty}
        for _, _, doc, eqty, _, _, _ in records
    ])
    match = match_production_inputs(wms, wme)
    evidence = {str(item["document"]): item for item in match.documents}
    assert match.residual_total == pytest.approx(-2100)
    for _, _, doc, _, diff, _, _ in records:
        assert evidence[doc]["status"] == "QTY_DIFF"
        assert evidence[doc]["difference"] == pytest.approx(diff)

    # No production cause is inferred from a bare quantity difference.
    investigation = ProductInvestigationResult(
        case_id="REAL-10002-BC-REVIEW", product_code="10002",
        product_name="CUTIE FRESH", unit="BUC",
        period="2026-01-02", report_date="2026-10-14",
        initial_difference=0, verdict="REVIEW",
        unexplained_difference=0,
        cause_status="NEDETERMINATA",
        findings=[
            {"title": "BC " + doc, "description":
             f"WMS {wqty} BUC; WME {eqty} BUC; diferenta {diff} BUC; "
             "posibila eroare de operator, neconfirmata ca defect software."}
            for _, wqty, doc, eqty, diff, _, _ in records
        ],
        conclusion_traceability=[
            {"step": "REAL_BC", "source": "WMS/WME", "key":
             f"BC={doc} WMS_ROW={wr} WME_ROW={er}", "rule": "QTY_DIFF",
             "result": f"{diff} BUC; HUMAN_VALIDATED_CONSUM",
             "evidence_level": "D"}
            for _, _, doc, _, diff, wr, er in records
        ],
    )
    report = build_case_report(
        investigation, engine_version="test", engine_commit_sha="PR43",
    )
    assert report.verdict == "REVIEW"
    assert len(report.conclusion_traceability) == 4
    output = tmp_path / "case.docx"
    generate_docx_report(report, output)
    with ZipFile(output) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    for _, _, doc, _, diff, wr, er in records:
        assert f"BC={doc}" in xml
        assert f"WMS_ROW={wr}" in xml
        assert f"WME_ROW={er}" in xml
        assert str(diff) in xml
