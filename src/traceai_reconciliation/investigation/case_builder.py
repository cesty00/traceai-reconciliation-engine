from __future__ import annotations

from datetime import datetime, timezone

from traceai_reconciliation.reports import CaseReport, Recommendation

from .models import ProductInvestigationResult


def build_case_report(
    result: ProductInvestigationResult,
    engine_version: str,
    engine_commit_sha: str = "LOCAL_OR_UNSET",
    rules_version: str = "0.1",
    execution_id: str | None = None,
) -> CaseReport:
    recommendations = [
        Recommendation(
            priority=item.get("priority", "P1"),
            action_type=item.get("action_type", "IMEDIATA"),
            recommendation=item.get("recommendation", "Continuarea verificării pe documentele sursă."),
            proposed_owner=item.get("proposed_owner"),
            precondition=item.get("precondition"),
        )
        for item in result.recommendations
    ]

    if execution_id is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        execution_id = f"RUN-{result.case_id}-{stamp}"

    executive_summary = (
        f"Produsul {result.product_code} - {result.product_name} a fost verificat automat "
        f"pe sursele WMS, WME, producție și stoc inițial disponibile. "
        f"Diferența inițială este {result.initial_difference:.3f} {result.unit}. "
        f"Verdictul tehnic curent este {result.verdict}, iar statusul cauzei este "
        f"{result.cause_status}. Motorul nu forțează închiderea cazului dacă dovezile "
        f"nu sunt suficiente."
    )

    # Surface independently computed BC discrepancies in the operator report.
    # Original physical source-row coordinates and human approval are NOT
    # inferred here; those require verified indexed provenance and review.
    bc_data = result.details.get("production_input_matching", {})
    bc_trace = []
    for item in bc_data.get("persistent_residual_documents", []):
        if item.get("status") != "QTY_DIFF":
            continue
        bc_trace.append({
            "step": "PRODUCTION_INPUT_BC",
            "source": "WMS PRODUCTION-IN vs WME BC",
            "key": "BC=" + str(item["document"]),
            "rule": "QTY_DIFF_NO_AUTO_CONVERSION",
            "result": (
                f"WMS={float(item['wms_effective']):.3f}; "
                f"WME={float(item['wme_bc']):.3f}; "
                f"DIFF={float(item['difference']):.3f}; "
                "SOURCE_ROWS_NOT_VERIFIED; HUMAN_VALIDATION_NOT_ATTACHED"
            ),
            "evidence_level": "D",
        })

    return CaseReport(
        case_id=result.case_id,
        product_code=result.product_code,
        product_name=result.product_name,
        period=result.period,
        report_date=result.report_date,
        initial_difference=result.initial_difference,
        explained_difference=result.explained_difference,
        unexplained_difference=result.unexplained_difference,
        unit=result.unit,
        verdict=result.verdict,
        evidence_level=result.evidence_level,
        cause_code=result.cause_code,
        cause_description=result.cause_description,
        cause_status=result.cause_status,
        executive_summary=executive_summary,
        sources_used=result.sources_used,
        findings=result.findings,
        recommendations=recommendations,
        operation_timeline=result.operation_timeline,
        unmatched_operations=result.unmatched_operations,
        conclusion_traceability=[*result.conclusion_traceability, *bc_trace],
        case_status=(
            "IN_ANALIZA"
            if (
                result.verdict == "REVIEW"
                and abs(result.unexplained_difference) > 0.001
            )
            else "ASTEPTARE_VALIDARE"
        ),
        human_intervention_required=True,
        execution_id=execution_id,
        engine_version=engine_version,
        engine_commit_sha=engine_commit_sha,
        rules_version=rules_version,
        source_hashes=result.source_hashes,
        technical_warnings=result.technical_warnings,
    )
