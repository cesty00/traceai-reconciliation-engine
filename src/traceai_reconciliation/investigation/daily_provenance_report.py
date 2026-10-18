"""Explicit, fail-closed adapter from Daily movement evidence to a DOCX CaseReport.

This adapter does not change reconciliation verdicts or reconcile documents.
It must be invoked by the caller after the indexed movement window is built.
"""
from __future__ import annotations

from traceai_reconciliation.reports.report_model import CaseReport
from .delta_movement_window import DeltaMovementWindowResult


def append_daily_source_provenance(
    report: CaseReport,
    movement_window: DeltaMovementWindowResult,
) -> CaseReport:
    manifest = movement_window.source_manifest
    if not manifest or set(manifest) != {"wms", "wme", "production"}:
        raise ValueError("Daily provenance missing complete source manifest")
    for system, source in manifest.items():
        digest = source.get("sha256", "")
        name = source.get("file_name", "")
        if len(digest) != 64 or not all(c in "0123456789abcdefABCDEF" for c in digest) or not name:
            raise ValueError(f"Daily provenance invalid source identity for {system}")

    references = []
    for system, rows in (
        ("wms", movement_window.wms_rows),
        ("wme", movement_window.wme_rows),
        ("production", movement_window.production_rows),
    ):
        for row in rows:
            line = row.get("SourceRowNumber")
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                raise ValueError(f"Daily provenance missing row coordinate for {system}")
            source = manifest[system]
            references.append({
                "step": "DAILY_SOURCE_ROW",
                "source": f"{system}: {source['file_name']}",
                "key": f"SHA256={source['sha256']} ROW={line}",
                "rule": "SOURCE_PROVENANCE_ONLY",
                "result": "Documentary reference, not economic MATCH",
                "evidence_level": "D",
            })
    # Mutate only after all evidence checks pass.
    report.source_hashes.update({
        f"daily_{system}": manifest[system]["sha256"] for system in manifest
    })
    report.conclusion_traceability.extend(references)
    return report
