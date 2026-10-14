"""Attach independently verified Daily row provenance to generated case artifacts."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from traceai_reconciliation.reports import case_report_from_dict, generate_docx_report

from .daily_delta_analysis import DailyDeltaRootCauseSummary
from .delta_movement_window import DeltaMovementWindowResult
from .daily_provenance_report import append_daily_source_provenance


def enrich_daily_case_reports(
    *, summary: DailyDeltaRootCauseSummary, cases_root: str | Path,
) -> tuple[str, ...]:
    updated: list[str] = []
    for item in summary.items:
        if item.reason != "ANALYZED" or not item.analysis:
            continue
        raw = item.analysis.get("movement_window")
        if not isinstance(raw, dict):
            raise ValueError(f"{item.case_id}: Daily movement evidence missing")
        if str(raw.get("product_code")) != str(item.product_code):
            raise ValueError(f"{item.case_id}: Daily product identity mismatch")
        case_dir = Path(cases_root) / item.case_id.replace("/", "_")
        case_path = case_dir / "case.json"
        docx_path = case_dir / "case.docx"
        if not case_path.is_file() or not docx_path.is_file():
            # Failed/skipped self-service cases are handled by the batch gate.
            continue
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("case_report"), dict):
            raise ValueError(f"{item.case_id}: invalid case.json")
        report = case_report_from_dict(payload["case_report"])
        if report.case_id != item.case_id or report.product_code != item.product_code:
            raise ValueError(f"{item.case_id}: case output identity mismatch")
        window = DeltaMovementWindowResult(**raw)
        append_daily_source_provenance(report, window)
        payload["case_report"] = asdict(report)

        # Stage both replacements; any failure blocks Daily completion.
        candidate_docx = docx_path.with_name("case.docx.provenance.tmp")
        candidate_json = case_path.with_name("case.json.provenance.tmp")
        try:
            generate_docx_report(report, candidate_docx)
            candidate_json.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            candidate_docx.replace(docx_path)
            candidate_json.replace(case_path)
        finally:
            candidate_docx.unlink(missing_ok=True)
            candidate_json.unlink(missing_ok=True)
        updated.append(item.case_id)
    return tuple(updated)
