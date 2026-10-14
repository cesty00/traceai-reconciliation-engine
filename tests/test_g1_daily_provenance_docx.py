from zipfile import ZipFile
import pytest
from traceai_reconciliation.investigation.daily_provenance_report import append_daily_source_provenance
from traceai_reconciliation.investigation.delta_movement_window import DeltaMovementWindowResult
from traceai_reconciliation.reports import CaseReport, generate_docx_report


def report():
    return CaseReport(
        case_id="CASE-G1", product_code="10002", product_name="CUTIE",
        period="2026", report_date="2026-10-14", initial_difference=1,
        explained_difference=0, unexplained_difference=1, unit="BUC",
        verdict="REVIEW", evidence_level="D", cause_code="UNKNOWN",
        cause_description="NEVERIFICAT", cause_status="NEDETERMINATA",
        executive_summary="Nu exista cauza demonstrata.",
    )


def window(row=15):
    manifest = {
        key: {"file_name": key + ".source", "sha256": char * 64}
        for key, char in (("wms", "a"), ("wme", "b"), ("production", "c"))
    }
    return DeltaMovementWindowResult(
        product_code="10002", product_name="CUTIE",
        start_exclusive="2026-10-11", end_inclusive="2026-10-12",
        wms_count=0, wme_count=1, production_count=0,
        wms_rows=(), wme_rows=({"SourceRowNumber": row, "Document": "23130"},),
        production_rows=(), source_manifest=manifest,
    )


def test_provenance_reaches_actual_docx(tmp_path):
    case = append_daily_source_provenance(report(), window())
    output = tmp_path / "case.docx"
    generate_docx_report(case, output)
    with ZipFile(output) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "ROW=15" in xml
    assert "b" * 64 in xml
    assert "wme.source" in xml
    assert case.verdict == "REVIEW"
    assert case.explained_difference == 0


def test_provenance_fails_closed_without_row():
    case = report()
    with pytest.raises(ValueError, match="row coordinate"):
        append_daily_source_provenance(case, window(row=None))
    assert case.source_hashes == {}
    assert case.conclusion_traceability == []
