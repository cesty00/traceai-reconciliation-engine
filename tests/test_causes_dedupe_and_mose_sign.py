from pathlib import Path
from docx import Document
from traceai_reconciliation.reports.report_model import CaseReport
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx

def test_duplicate_pv_and_signed_mose_source_rows(tmp_path: Path):
    report=CaseReport(case_id="CASE-X",product_code="X",product_name="X",
        period="2026",report_date="2026-10-15",initial_difference=0,
        explained_difference=0,unexplained_difference=0,unit="kg",
        verdict="REVIEW",evidence_level="B",cause_code="REVIEW",
        cause_description="Review",cause_status="NEDETERMINATA",
        executive_summary="Review",
        unmatched_operations=[
            {"system":"WME","document":"2613","operation_type":"PV","quantity":5.95,"date":"2026-08-29","reason":"PV review"},
            {"system":"WME","document":"2613","operation_type":"PV","quantity":5.95,"date":"-","reason":"Duplicat rezidual"},
            {"system":"WME","document":"92766","operation_type":"F","quantity":20,"date":"-","reason":"MOSE efect 20"},
        ],
        operation_timeline=[
            {"system":"WME","document":"2613","operation_type":"PV","quantity":-5.95,"date":"2026-08-29 00:00:00","warehouse":"DEPOZIT PRINCIPAL"},
            {"system":"WME","document":"92766","operation_type":"F","quantity":-20,"date":"2026-05-06 00:00:00","warehouse":"MOSE"},
        ])
    output=generate_operator_causes_docx(report,tmp_path/"case.docx")
    doc=Document(output)
    text=" ".join(c.text for t in doc.tables for row in t.rows for c in row.cells)
    assert text.count("2613")==1
    assert "06.05.2026" in text
    assert "MOSE" in text
    assert "-20" in text
