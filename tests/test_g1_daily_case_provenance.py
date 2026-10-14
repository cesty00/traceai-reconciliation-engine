import json
from dataclasses import asdict
from zipfile import ZipFile
import pytest

from traceai_reconciliation.investigation.daily_case_provenance import enrich_daily_case_reports
from traceai_reconciliation.investigation.daily_delta_analysis import DailyDeltaRootCauseItem, DailyDeltaRootCauseSummary
from traceai_reconciliation.investigation.delta_movement_window import DeltaMovementWindowResult
from traceai_reconciliation.reports import CaseReport, generate_docx_report


def test_daily_case_artifacts_enriched_and_fail_closed(tmp_path):
    case_id = "CASE-G1"
    case_dir = tmp_path / case_id
    case_dir.mkdir()
    report = CaseReport(
        case_id=case_id, product_code="10002", product_name="CUTIE",
        period="2026", report_date="2026-10-14", initial_difference=1,
        explained_difference=0, unexplained_difference=1, unit="BUC",
        verdict="REVIEW", evidence_level="D", cause_code="UNKNOWN",
        cause_description="NEVERIFICAT", cause_status="NEDETERMINATA",
        executive_summary="Nu exista cauza demonstrata.",
    )
    (case_dir / "case.json").write_text(
        json.dumps({"case_report": asdict(report)}), encoding="utf-8"
    )
    generate_docx_report(report, case_dir / "case.docx")
    manifest = {
        key: {"file_name": key + ".source", "sha256": char * 64}
        for key, char in (("wms", "a"), ("wme", "b"), ("production", "c"))
    }
    window = DeltaMovementWindowResult(
        product_code="10002", product_name="CUTIE",
        start_exclusive="2026-10-11", end_inclusive="2026-10-12",
        wms_count=0, wme_count=1, production_count=0,
        wms_rows=(), wme_rows=({"SourceRowNumber": 15, "Document": "23130"},),
        production_rows=(), source_manifest=manifest,
    )
    item = DailyDeltaRootCauseItem(
        case_id=case_id, product_code="10002", status="UNEXPLAINED",
        reason="ANALYZED", analysis={"movement_window": asdict(window)},
    )
    summary = DailyDeltaRootCauseSummary(
        previous_snapshot_at="2026-10-11", current_snapshot_at="2026-10-12",
        analyzed=1, skipped=0, exact_event=0, multi_event=0,
        unexplained=1, items=(item,),
    )
    assert enrich_daily_case_reports(summary=summary, cases_root=tmp_path) == (case_id,)
    saved = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert saved["case_report"]["verdict"] == "REVIEW"
    assert saved["case_report"]["source_hashes"]["daily_wme"] == "b" * 64
    with ZipFile(case_dir / "case.docx") as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "ROW=15" in xml and "b" * 64 in xml

    broken = asdict(window)
    broken["wme_rows"] = [{"SourceRowNumber": None}]
    invalid = DailyDeltaRootCauseItem(
        case_id=case_id, product_code="10002", status="UNEXPLAINED",
        reason="ANALYZED", analysis={"movement_window": broken},
    )
    bad_summary = DailyDeltaRootCauseSummary(
        previous_snapshot_at="2026-10-11", current_snapshot_at="2026-10-12",
        analyzed=1, skipped=0, exact_event=0, multi_event=0,
        unexplained=1, items=(invalid,),
    )
    before = (case_dir / "case.json").read_bytes()
    with pytest.raises(ValueError, match="row coordinate"):
        enrich_daily_case_reports(summary=bad_summary, cases_root=tmp_path)
    assert (case_dir / "case.json").read_bytes() == before
