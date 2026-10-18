from pathlib import Path

from traceai_reconciliation.reports.report_model import CaseReport
from traceai_reconciliation.reports.operator_causes_report import generate_operator_causes_docx
from docx import Document


def test_operator_report_displays_human_evidence_without_verdict_change(tmp_path):
    case = CaseReport(
        case_id="TEST", product_code="DS099902505", product_name="Test",
        period="2026", report_date="2026-10-18", initial_difference=-10,
        explained_difference=0, unexplained_difference=-10, unit="BUCATA",
        verdict="REVIEW", evidence_level="B", cause_code="PENDING",
        cause_description="Review", cause_status="NEDETERMINATA",
        executive_summary="Review",
    )
    evidence = [{
        "evidence_id": "HUM-DS099902505-273779", "system": "WMS",
        "source_row": 273779, "source_date": "2026-09-18",
        "signed_quantity": -10, "unit": "BUCATA",
        "physical_count_confirmed": True, "counterpart_wme_exists": False,
        "statement": "Confirmat fizic, numai WMS", "provenance": "Confirmare operator",
    }]
    path = generate_operator_causes_docx(case, tmp_path / "case.docx", human_evidence=evidence)
    content = "\n".join(p.text for p in Document(path).paragraphs)
    assert "HUM-DS099902505-273779" in content
    assert "273779" in content
    assert "nu schimbă verdictul general REVIEW" in content
    assert case.verdict == "REVIEW"
    assert case.explained_difference == 0
