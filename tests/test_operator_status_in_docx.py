from pathlib import Path
from docx import Document
from traceai_reconciliation.reports.report_model import CaseReport
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx

def test_operational_status_printed_on_every_cause(tmp_path: Path):
    report = CaseReport(
        case_id="CASE-STATUS", product_code="X", product_name="X",
        period="2026", report_date="2026-10-15", initial_difference=0,
        explained_difference=0, unexplained_difference=0, unit="kg",
        verdict="REVIEW", evidence_level="B", cause_code="REVIEW",
        cause_description="Review", cause_status="NEDETERMINATA",
        executive_summary="Review",
        findings=[{"type":"RECEPTION_STAGING_INCLUDED_IN_STORAGE"}],
        operation_timeline=[
            dict(system="WMS",document="SFA24774",operation_type="Livrare",quantity=-2700,date="2026-10-01",warehouse="Depozit Principal"),
            dict(system="WMS",document="SFA24774-1",operation_type="Receptie",quantity=300,date="2026-10-02",warehouse="Depozit Principal"),
            dict(system="WME",document="24774",operation_type="AE",quantity=-2400,date="2026-10-01",warehouse="DEPOZIT PRINCIPAL"),
            dict(system="WME",document="92766",operation_type="F",quantity=-20,date="2026-05-06",warehouse="MOSE"),
        ],
        unmatched_operations=[
            dict(system="WME",document="2446",operation_type="PV",quantity=-0.9,reason="PV REVIEW"),
            dict(system="WME",document="92766",operation_type="F",quantity=20,reason="MOSE REVIEW"),
        ],
    )
    target=generate_operator_causes_docx(report,tmp_path/"case.docx")
    paragraphs=[p.text for p in Document(target).paragraphs]
    statuses=[p for p in paragraphs if p.startswith("Stadiu operațional:")]
    assert len(statuses)==4
    assert statuses[0]=="Stadiu operațional: EXPLICAT"
    assert all("REVIEW" in status for status in statuses[1:])
    assert "CORECȚIE PROPUSĂ" not in " ".join(statuses)
