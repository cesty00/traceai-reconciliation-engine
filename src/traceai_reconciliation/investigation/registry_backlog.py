from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .batch import BatchCaseSpec


def _number(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0.0
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    elif "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def load_registry_export(
    path: str | Path,
) -> list[dict[str, Any]]:
    source = Path(path)
    suffix = source.suffix.lower()

    if suffix == ".csv":
        with source.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    if suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("rows", payload.get("cases", []))
        if not isinstance(payload, list):
            raise ValueError(
                "Registry JSON must be a list or an object with rows/cases."
            )
        return [
            dict(item)
            for item in payload
            if isinstance(item, dict)
        ]

    raise ValueError("Registry export must be .csv or .json.")


def select_registry_cases(
    rows: Iterable[dict[str, Any]],
    *,
    statuses: set[str] | None = None,
    limit: int | None = None,
    exclude_case_ids: set[str] | None = None,
    exclude_products: set[str] | None = None,
) -> list[BatchCaseSpec]:
    """
    Convert REGISTRU_CAZURI rows into a deterministic batch selection.

    Default scope: DESCHIS + IN_ANALIZA only, ordered by absolute stock
    difference descending, then CASE_ID.
    """
    wanted_statuses = {
        item.strip().upper()
        for item in (statuses or {"DESCHIS", "IN_ANALIZA"})
        if item.strip()
    }
    excluded_cases = {
        item.strip()
        for item in (exclude_case_ids or set())
        if item.strip()
    }
    excluded_products = {
        item.strip()
        for item in (exclude_products or set())
        if item.strip()
    }

    candidates: list[tuple[float, str, BatchCaseSpec]] = []
    seen_case_ids: set[str] = set()

    for row in rows:
        case_id = str(row.get("CASE_ID", "")).strip()
        product_code = str(row.get("Cod_produs", "")).strip()
        period = str(row.get("Perioada_WMS", "")).strip()
        status = str(
            row.get("Status_investigatie", "")
        ).strip().upper()

        if not case_id or not product_code or not period:
            continue
        if case_id in seen_case_ids:
            continue
        if status not in wanted_statuses:
            continue
        if case_id in excluded_cases:
            continue
        if product_code in excluded_products:
            continue

        difference = _number(row.get("Diferenta"))
        candidates.append(
            (
                abs(difference),
                case_id,
                BatchCaseSpec(
                    case_id=case_id,
                    product_code=product_code,
                    period=period.replace("–", "-"),
                    report_date=None,
                    enabled=True,
                ),
            )
        )
        seen_case_ids.add(case_id)

    candidates.sort(
        key=lambda item: (-item[0], item[1])
    )
    selected = [item[2] for item in candidates]

    if limit is not None:
        if limit < 0:
            raise ValueError("Batch limit must be >= 0.")
        selected = selected[:limit]

    return selected


def manifest_payload(
    cases: list[BatchCaseSpec],
) -> dict[str, Any]:
    return {
        "cases": [
            {
                "case_id": case.case_id,
                "product_code": case.product_code,
                "period": case.period,
                "report_date": case.report_date,
                "enabled": case.enabled,
            }
            for case in cases
        ]
    }


def write_manifest(
    path: str | Path,
    cases: list[BatchCaseSpec],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            manifest_payload(cases),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(output)
    return output
