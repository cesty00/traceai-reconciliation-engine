from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from . import __version__
from .investigation import (
    InvestigationSources,
    build_case_report,
    build_registry_update,
    investigate_product,
    load_batch_manifest,
    run_batch,
    load_registry_export,
    select_registry_cases,
    write_manifest,
    build_registry_apply_plan,
    write_registry_apply_plan,
    run_self_service_case,
    run_self_service_batch,
)
from .loaders import read_table
from .product_audit import summarize_stock_report
from .reports import generate_docx_report, load_case_report_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TraceAI WMS-WME product reconciliation audit"
    )
    parser.add_argument("--stock-report", help="Local XLSX/CSV stock report")
    parser.add_argument("--product", help="Product code to investigate")
    parser.add_argument("--case-json", help="Structured CaseReport JSON input")
    parser.add_argument("--output-docx", help="DOCX output path")
    parser.add_argument("--output-json", help="Technical JSON output path")
    parser.add_argument(
        "--output-registry-json",
        help=(
            "Optional deterministic REGISTRU_CAZURI upsert payload JSON. "
            "No Google credentials are stored or used by the engine."
        ),
    )
    parser.add_argument("--case-id", help="CASE_ID for product investigation")
    parser.add_argument(
        "--batch-summary",
        help="Existing batch_summary.json used to stage registry updates",
    )
    parser.add_argument(
        "--registry-plan-output",
        help="Output JSON path for a staged registry apply plan",
    )
    parser.add_argument(
        "--minimum-evidence",
        default="B",
        choices=["A", "B", "C", "D"],
        help="Minimum evidence level accepted by registry apply-plan staging",
    )
    parser.add_argument(
        "--registry-export",
        help="CSV/JSON export of REGISTRU_CAZURI used to build a batch manifest",
    )
    parser.add_argument(
        "--manifest-output",
        help="Output JSON path for a manifest generated from REGISTRU_CAZURI",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        help="Maximum number of registry cases selected into a generated manifest",
    )
    parser.add_argument(
        "--registry-status",
        action="append",
        help=(
            "Registry status to include when generating a manifest. "
            "Can be repeated. Defaults to DESCHIS and IN_ANALIZA."
        ),
    )
    parser.add_argument(
        "--exclude-case-id",
        action="append",
        help="CASE_ID to exclude from generated backlog manifest; repeatable",
    )
    parser.add_argument(
        "--exclude-product",
        action="append",
        help="Product code to exclude from generated backlog manifest; repeatable",
    )
    parser.add_argument(
        "--batch-manifest",
        help="JSON/CSV manifest for controlled multi-case execution",
    )
    parser.add_argument(
        "--batch-output-dir",
        help="Output directory for batch case folders and batch_summary.json",
    )
    parser.add_argument(
        "--batch-id",
        help="Deterministic batch execution identifier",
    )
    parser.add_argument(
        "--no-reuse-completed",
        action="store_true",
        help="Force re-execution even when a complete case signature can be reused",
    )
    parser.add_argument("--period", help="Investigation period label")
    parser.add_argument("--report-date", help="Report date")
    parser.add_argument(
        "--self-service-output-dir",
        help="Run v0.8 single-case self-service workflow into this directory",
    )
    parser.add_argument(
        "--self-service-batch-manifest",
        help="JSON/CSV manifest for v0.8 self-service batch execution",
    )
    parser.add_argument(
        "--self-service-batch-output-dir",
        help="Output directory for v0.8 self-service batch execution",
    )
    parser.add_argument("--opening-stock-wms", help="Opening stock WMS XLSX")
    parser.add_argument(
        "--opening-absent-means-zero",
        action="store_true",
        help=(
            "Explicit policy for a complete opening-stock export: if the product "
            "is absent from that file, treat its WMS opening balance as 0. "
            "Disabled by default."
        ),
    )
    parser.add_argument("--wms-movements", help="WMS movements CSV/XLSX")
    parser.add_argument("--wme-ledger", help="WME stock ledger XLSX")
    parser.add_argument("--production", help="Production CSV/XLSX")
    parser.add_argument("--nomenclature", help="WME-WMS nomenclature XLSX")
    parser.add_argument(
        "--indexed-cache",
        action="store_true",
        help=(
            "Build/reuse a local SQLite index for large WMS/WME/production "
            "sources. Recommended for repeated product investigations."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        help=(
            "Optional local cache directory. Defaults to .traceai_cache "
            "beside --output-docx for real investigations."
        ),
    )
    parser.add_argument(
        "--engine-commit-sha",
        default="LOCAL_OR_UNSET",
        help="Git commit SHA recorded in the generated report",
    )
    parser.add_argument(
        "--rules-version",
        default="0.4",
        help="Rules version recorded in the generated report",
    )
    return parser


def _write_json(path: str | Path, payload: dict) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return output


def _run_registry_apply_plan_generation(
    args: argparse.Namespace,
) -> None:
    required = {
        "--registry-export": args.registry_export,
        "--batch-summary": args.batch_summary,
        "--registry-plan-output": args.registry_plan_output,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(
            "Registry apply-plan generation requires: "
            + ", ".join(missing)
        )

    rows = load_registry_export(args.registry_export)
    plan = build_registry_apply_plan(
        rows,
        args.batch_summary,
        minimum_evidence=args.minimum_evidence,
    )
    output = write_registry_apply_plan(
        args.registry_plan_output,
        plan,
    )
    print(
        json.dumps(
            {
                "registry_apply_plan": str(output),
                "batch_id": plan.get("batch_id"),
                "counts": plan.get("counts", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _run_registry_manifest_generation(
    args: argparse.Namespace,
) -> None:
    if not args.registry_export or not args.manifest_output:
        raise SystemExit(
            "Registry manifest generation requires "
            "--registry-export and --manifest-output."
        )

    rows = load_registry_export(args.registry_export)
    statuses = (
        set(args.registry_status)
        if args.registry_status
        else None
    )
    cases = select_registry_cases(
        rows,
        statuses=statuses,
        limit=args.batch_limit,
        exclude_case_ids=set(args.exclude_case_id or []),
        exclude_products=set(args.exclude_product or []),
    )
    output = write_manifest(args.manifest_output, cases)
    print(
        json.dumps(
            {
                "manifest": str(output),
                "selected_cases": len(cases),
                "case_ids": [case.case_id for case in cases],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _run_batch_investigation(args: argparse.Namespace) -> None:
    required = {
        "--batch-manifest": args.batch_manifest,
        "--batch-output-dir": args.batch_output_dir,
        "--batch-id": args.batch_id,
        "--stock-report": args.stock_report,
        "--opening-stock-wms": args.opening_stock_wms,
        "--wms-movements": args.wms_movements,
        "--wme-ledger": args.wme_ledger,
        "--production": args.production,
        "--nomenclature": args.nomenclature,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(
            "Batch investigation requires: " + ", ".join(missing)
        )

    output_dir = Path(args.batch_output_dir)
    cache_dir = (
        Path(args.cache_dir)
        if args.cache_dir
        else output_dir / ".traceai_cache"
    )
    sources = InvestigationSources(
        stock_report=Path(args.stock_report),
        opening_stock_wms=Path(args.opening_stock_wms),
        wms_movements=Path(args.wms_movements),
        wme_ledger=Path(args.wme_ledger),
        production=Path(args.production),
        nomenclature=Path(args.nomenclature),
        cache_dir=cache_dir,
        use_source_index=True,
        opening_absent_means_zero=args.opening_absent_means_zero,
    )

    cases = load_batch_manifest(args.batch_manifest)
    summary = run_batch(
        cases,
        sources,
        output_dir,
        batch_id=args.batch_id,
        rules_version=args.rules_version,
        engine_commit_sha=args.engine_commit_sha,
        reuse_completed=not args.no_reuse_completed,
    )
    print(
        json.dumps(
            asdict(summary),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def _run_self_service_batch_investigation(
    args: argparse.Namespace,
) -> None:
    required = {
        "--self-service-batch-manifest": args.self_service_batch_manifest,
        "--self-service-batch-output-dir": args.self_service_batch_output_dir,
        "--batch-id": args.batch_id,
        "--stock-report": args.stock_report,
        "--opening-stock-wms": args.opening_stock_wms,
        "--wms-movements": args.wms_movements,
        "--wme-ledger": args.wme_ledger,
        "--production": args.production,
        "--nomenclature": args.nomenclature,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(
            "Self-service batch requires: " + ", ".join(missing)
        )

    output_dir = Path(args.self_service_batch_output_dir)
    cache_dir = (
        Path(args.cache_dir)
        if args.cache_dir
        else output_dir / ".traceai_cache"
    )
    sources = InvestigationSources(
        stock_report=Path(args.stock_report),
        opening_stock_wms=Path(args.opening_stock_wms),
        wms_movements=Path(args.wms_movements),
        wme_ledger=Path(args.wme_ledger),
        production=Path(args.production),
        nomenclature=Path(args.nomenclature),
        cache_dir=cache_dir,
        use_source_index=args.indexed_cache,
        opening_absent_means_zero=args.opening_absent_means_zero,
    )
    cases = load_batch_manifest(args.self_service_batch_manifest)
    summary = run_self_service_batch(
        cases=cases,
        sources=sources,
        output_dir=output_dir,
        batch_id=args.batch_id,
        rules_version=args.rules_version,
        engine_commit_sha=args.engine_commit_sha,
    )
    print(
        json.dumps(
            asdict(summary),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def _run_self_service_investigation(args: argparse.Namespace) -> None:
    required = {
        "--product": args.product,
        "--period": args.period,
        "--stock-report": args.stock_report,
        "--opening-stock-wms": args.opening_stock_wms,
        "--wms-movements": args.wms_movements,
        "--wme-ledger": args.wme_ledger,
        "--production": args.production,
        "--nomenclature": args.nomenclature,
        "--self-service-output-dir": args.self_service_output_dir,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(
            "Self-service investigation requires: " + ", ".join(missing)
        )

    output_dir = Path(args.self_service_output_dir)
    cache_dir = (
        Path(args.cache_dir)
        if args.cache_dir
        else output_dir / ".traceai_cache"
    )
    sources = InvestigationSources(
        stock_report=Path(args.stock_report),
        opening_stock_wms=Path(args.opening_stock_wms),
        wms_movements=Path(args.wms_movements),
        wme_ledger=Path(args.wme_ledger),
        production=Path(args.production),
        nomenclature=Path(args.nomenclature),
        cache_dir=cache_dir,
        use_source_index=args.indexed_cache,
        opening_absent_means_zero=args.opening_absent_means_zero,
    )
    result = run_self_service_case(
        product_code=args.product,
        case_id=args.case_id,
        period=args.period,
        report_date=args.report_date,
        sources=sources,
        output_dir=output_dir,
        rules_version=args.rules_version,
        engine_commit_sha=args.engine_commit_sha,
        execution_id=f"self-service:{args.case_id or args.product}",
    )
    print(
        json.dumps(
            asdict(result),
            ensure_ascii=False,
            indent=2,
        )
    )


def _run_real_product_investigation(args: argparse.Namespace) -> None:
    required = {
        "--product": args.product,
        "--case-id": args.case_id,
        "--period": args.period,
        "--stock-report": args.stock_report,
        "--opening-stock-wms": args.opening_stock_wms,
        "--wms-movements": args.wms_movements,
        "--wme-ledger": args.wme_ledger,
        "--production": args.production,
        "--nomenclature": args.nomenclature,
        "--output-docx": args.output_docx,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit(
            "Real product investigation requires: " + ", ".join(missing)
        )

    output_docx = Path(args.output_docx)
    cache_dir = (
        Path(args.cache_dir)
        if args.cache_dir
        else output_docx.parent / ".traceai_cache"
    )

    sources = InvestigationSources(
        stock_report=Path(args.stock_report),
        opening_stock_wms=Path(args.opening_stock_wms),
        wms_movements=Path(args.wms_movements),
        wme_ledger=Path(args.wme_ledger),
        production=Path(args.production),
        nomenclature=Path(args.nomenclature),
        cache_dir=cache_dir,
        use_source_index=args.indexed_cache,
        opening_absent_means_zero=args.opening_absent_means_zero,
    )

    result = investigate_product(
        product_code=args.product,
        case_id=args.case_id,
        sources=sources,
        period=args.period,
        report_date=args.report_date,
    )
    case_report = build_case_report(
        result,
        engine_version=__version__,
        engine_commit_sha=args.engine_commit_sha,
        rules_version=args.rules_version,
    )

    registry_update = build_registry_update(
        result,
        case_report,
    )
    technical_payload = {
        "investigation": asdict(result),
        "case_report": asdict(case_report),
        "registry_update": registry_update,
    }

    if args.output_json:
        _write_json(args.output_json, technical_payload)

    if args.output_registry_json:
        _write_json(args.output_registry_json, registry_update)

    output = generate_docx_report(case_report, args.output_docx)
    print(str(output))


def main() -> None:
    args = build_parser().parse_args()

    if args.registry_export and args.batch_summary:
        _run_registry_apply_plan_generation(args)
        return

    if args.registry_export:
        _run_registry_manifest_generation(args)
        return

    if args.self_service_batch_manifest:
        _run_self_service_batch_investigation(args)
        return

    if args.batch_manifest:
        _run_batch_investigation(args)
        return

    if args.self_service_output_dir:
        _run_self_service_investigation(args)
        return

    if args.case_json:
        if not args.output_docx:
            raise SystemExit("--output-docx is required together with --case-json")
        case_report = load_case_report_json(args.case_json)
        output = generate_docx_report(case_report, args.output_docx)
        print(str(output))
        return

    real_investigation_requested = any(
        [
            args.opening_stock_wms,
            args.wms_movements,
            args.wme_ledger,
            args.production,
            args.nomenclature,
            args.case_id,
        ]
    )
    if real_investigation_requested:
        _run_real_product_investigation(args)
        return

    if not args.stock_report or not args.product:
        raise SystemExit(
            "Use --stock-report and --product for stock audit, "
            "--case-json and --output-docx for DOCX generation, "
            "or provide all v0.3 investigation source arguments."
        )

    stock_report = read_table(args.stock_report)
    audit = summarize_stock_report(stock_report, args.product)
    print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
