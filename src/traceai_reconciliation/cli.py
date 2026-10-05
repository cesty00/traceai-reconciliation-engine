from __future__ import annotations

import argparse
from dataclasses import asdict
import json

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
    parser.add_argument("--output-docx", help="DOCX output path for --case-json")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.case_json:
        if not args.output_docx:
            raise SystemExit("--output-docx is required together with --case-json")
        case_report = load_case_report_json(args.case_json)
        output = generate_docx_report(case_report, args.output_docx)
        print(str(output))
        return

    if not args.stock_report or not args.product:
        raise SystemExit(
            "Use --stock-report and --product for stock audit, "
            "or --case-json and --output-docx for DOCX generation."
        )

    stock_report = read_table(args.stock_report)
    audit = summarize_stock_report(stock_report, args.product)
    print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
