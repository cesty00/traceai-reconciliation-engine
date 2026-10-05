from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from .loaders import read_table
from .product_audit import summarize_stock_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TraceAI WMS-WME product reconciliation audit"
    )
    parser.add_argument("--stock-report", required=True, help="Local XLSX/CSV stock report")
    parser.add_argument("--product", required=True, help="Product code to investigate")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = read_table(args.stock_report)
    audit = summarize_stock_report(report, args.product)
    print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
