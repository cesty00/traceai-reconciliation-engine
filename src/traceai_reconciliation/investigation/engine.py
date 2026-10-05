from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .models import InvestigationSources, ProductInvestigationResult
from .source_readers import (
    first_non_empty,
    numeric_sum,
    read_excel_table,
    read_filtered,
    resolve_column,
    sha256_file,
)


def _row_value(row: pd.Series, columns: pd.Index, semantic: str, default: Any = "-") -> Any:
    column = resolve_column(columns, semantic, required=False)
    if column is None:
        return default
    value = row.get(column, default)
    if pd.isna(value):
        return default
    return value


def _timeline_from_frame(df: pd.DataFrame, system: str) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        entries.append(
            {
                "date": _row_value(row, df.columns, "date"),
                "system": system,
                "document": _row_value(row, df.columns, "document"),
                "operation_type": _row_value(row, df.columns, "operation_type"),
                "quantity": _row_value(row, df.columns, "quantity"),
                "warehouse": _row_value(row, df.columns, "warehouse"),
                "counterpart": "-",
                "verdict": "REVIEW",
                "note": "Operațiune extrasă automat pentru produs; matching-ul documentar se validează separat.",
            }
        )
    return entries


def _map_product_to_wme_ids(nomenclature: pd.DataFrame, product_code: str) -> tuple[set[str], list[str]]:
    warnings: list[str] = []
    if nomenclature.empty:
        return set(), ["Nomenclatorul este gol."]

    ds_col = resolve_column(nomenclature.columns, "wms_product_code")
    wme_col = resolve_column(nomenclature.columns, "wme_item_id")

    rows = nomenclature[
        nomenclature[ds_col].astype(str).str.strip() == str(product_code).strip()
    ].copy()
    ids = {
        str(value).strip()
        for value in rows[wme_col].dropna().tolist()
        if str(value).strip()
    }
    if not ids:
        warnings.append(
            f"Nu există mapare WME pentru produsul {product_code}; WME nu poate fi filtrat sigur."
        )
    if len(ids) > 1:
        warnings.append(
            f"Produsul {product_code} are {len(ids)} identificatori WME în nomenclator; cazul rămâne REVIEW."
        )
    return ids, warnings


def investigate_product(
    product_code: str,
    case_id: str,
    sources: InvestigationSources,
    period: str,
    report_date: str | None = None,
    decimals: int = 3,
) -> ProductInvestigationResult:
    report_date = report_date or date.today().isoformat()

    stock_report = read_excel_table(sources.stock_report)
    stock_code_col = resolve_column(stock_report.columns, "product_code")
    stock_rows = stock_report[
        stock_report[stock_code_col].astype(str).str.strip() == str(product_code).strip()
    ].copy()
    if stock_rows.empty:
        raise KeyError(f"Produsul {product_code} nu există în raportul de stoc.")

    product_name = first_non_empty(stock_rows, "product_name") or product_code
    unit = first_non_empty(stock_rows, "unit") or "UM"

    reported_wms = numeric_sum(stock_rows, "stock_wms")
    reported_wme = numeric_sum(stock_rows, "stock_wme")
    initial_difference = numeric_sum(stock_rows, "stock_difference")

    result = ProductInvestigationResult(
        case_id=case_id,
        product_code=product_code,
        product_name=product_name,
        unit=unit,
        period=period,
        report_date=report_date,
        initial_difference=round(initial_difference, decimals),
        reported_stock_wms=round(reported_wms, decimals),
        reported_stock_wme=round(reported_wme, decimals),
        unexplained_difference=round(initial_difference, decimals),
    )

    result.sources_used.extend(
        [
            {"source_id": "SRC-STOCK-REPORT", "name": sources.stock_report.name, "period": period, "role": "diferență de pornire", "status": "VERIFICAT"},
            {"source_id": "SRC-OPENING-WMS", "name": sources.opening_stock_wms.name, "period": "01.01.2026", "role": "stoc inițial WMS", "status": "VERIFICAT"},
            {"source_id": "SRC-WMS", "name": sources.wms_movements.name, "period": period, "role": "mișcări WMS", "status": "VERIFICAT"},
            {"source_id": "SRC-WME", "name": sources.wme_ledger.name, "period": period, "role": "fișă magazie WME", "status": "VERIFICAT"},
            {"source_id": "SRC-PROD", "name": sources.production.name, "period": period, "role": "producție", "status": "VERIFICAT"},
            {"source_id": "SRC-NOM", "name": sources.nomenclature.name, "period": "-", "role": "mapare produs WME-WMS", "status": "VERIFICAT"},
        ]
    )

    for key, path in {
        "stock_report": sources.stock_report,
        "opening_stock_wms": sources.opening_stock_wms,
        "wms_movements": sources.wms_movements,
        "wme_ledger": sources.wme_ledger,
        "production": sources.production,
        "nomenclature": sources.nomenclature,
    }.items():
        result.source_hashes[key] = sha256_file(path)

    opening_rows = read_filtered(sources.opening_stock_wms, "product_code", [product_code])
    if opening_rows.empty:
        result.technical_warnings.append(
            f"Produsul {product_code} nu a fost găsit în stocul inițial WMS."
        )
    else:
        result.opening_stock_wms = round(numeric_sum(opening_rows, "initial_stock"), decimals)

    wms_rows = read_filtered(sources.wms_movements, "product_code", [product_code])
    production_rows = read_filtered(sources.production, "product_code", [product_code])

    nomenclature = read_excel_table(sources.nomenclature)
    wme_ids, mapping_warnings = _map_product_to_wme_ids(nomenclature, product_code)
    result.technical_warnings.extend(mapping_warnings)

    if wme_ids:
        wme_rows = read_filtered(sources.wme_ledger, "wme_item_id", wme_ids)
    else:
        wme_rows = pd.DataFrame()

    if result.opening_stock_wms is not None:
        result.technical_warnings.append(
            "Reconstrucția cantitativă WMS este suspendată în acest checkpoint până la "
            "validarea semnului/direcției pentru fiecare tip de operațiune WMS. "
            "Rândurile WMS sunt extrase integral pentru produs, dar nu sunt însumate "
            "ca sold final fără o regulă operațională validată."
        )

    if not wme_rows.empty:
        balance_col = resolve_column(wme_rows.columns, "running_balance", required=False)
        if balance_col is not None:
            balance_values = pd.to_numeric(wme_rows[balance_col], errors="coerce").dropna()
            if not balance_values.empty:
                result.calculated_stock_wme = round(float(balance_values.iloc[-1]), decimals)
                gap = round(
                    (result.reported_stock_wme or 0.0) - result.calculated_stock_wme,
                    decimals,
                )
                result.findings.append(
                    {
                        "type": "WME_BALANCE_CHECK",
                        "description": (
                            f"Ultimul sold WME pentru produs: {result.calculated_stock_wme:.3f}; "
                            f"QuantityERP din raport: {(result.reported_stock_wme or 0.0):.3f}; "
                            f"abatere: {gap:.3f}."
                        ),
                        "evidence": "SRC-WME + SRC-STOCK-REPORT",
                    }
                )
        else:
            result.technical_warnings.append(
                "Coloana de sold rulant WME nu a fost identificată; soldul WME nu a fost reconstruit."
            )

    result.operation_timeline.extend(_timeline_from_frame(wms_rows, "WMS"))
    result.operation_timeline.extend(_timeline_from_frame(wme_rows, "WME"))
    result.operation_timeline.extend(_timeline_from_frame(production_rows, "PRODUCTIE"))

    result.operation_timeline.sort(key=lambda item: str(item.get("date", "")))

    result.details.update(
        {
            "stock_report_rows": len(stock_rows),
            "wms_rows": len(wms_rows),
            "wme_rows": len(wme_rows),
            "production_rows": len(production_rows),
            "wme_mapping_ids": sorted(wme_ids),
        }
    )

    result.findings.append(
        {
            "type": "SOURCE_COUNTS",
            "description": (
                f"Rânduri relevante extrase: WMS={len(wms_rows)}, "
                f"WME={len(wme_rows)}, producție={len(production_rows)}."
            ),
            "evidence": "filtrare automată pe produs",
        }
    )

    if not wme_ids:
        result.cause_code = "CAUSE-MASTER-DATA"
        result.cause_description = (
            "Maparea produsului WMS către identificatorul intern WME nu este disponibilă sau nu este sigură."
        )
        result.cause_status = "PROBABILA"
        result.evidence_level = "C"
        result.recommendations.append(
            {
                "priority": "P1",
                "action_type": "IMEDIATA",
                "recommendation": "Validarea mapării produsului WMS ↔ articol WME înaintea oricărei concluzii operaționale.",
                "proposed_owner": "Responsabil master data / verificare",
                "precondition": "Confirmare cod WME pentru produs",
            }
        )
    elif abs(result.initial_difference) <= 10 ** (-decimals):
        result.verdict = "MATCH_DIRECT"
        result.evidence_level = "A"
        result.cause_code = "CAUSE-NONE"
        result.cause_description = "Raportul de stoc nu indică diferență materială pentru produs."
        result.cause_status = "CONFIRMATA"
        result.explained_difference = 0.0
        result.unexplained_difference = 0.0
        result.recommendations.append(
            {
                "priority": "P3",
                "action_type": "PREVENTIVA",
                "recommendation": "Păstrarea cazului ca test de regresie pentru verificările viitoare.",
                "proposed_owner": "TraceAI Control",
                "precondition": "Surse validate",
            }
        )
    else:
        result.recommendations.append(
            {
                "priority": "P1",
                "action_type": "IMEDIATA",
                "recommendation": (
                    "Compararea document cu document a operațiunilor WMS și WME extrase pentru produs, "
                    "înaintea oricărei ajustări de stoc."
                ),
                "proposed_owner": "Responsabil verificare",
                "precondition": "Surse și mapare produs validate",
            }
        )
        result.recommendations.append(
            {
                "priority": "P4",
                "action_type": "AUTOMATIZARE_CONTROL",
                "recommendation": (
                    "Aplicarea în etapa următoare a matching-ului operațional WMS↔WME pentru identificarea "
                    "operațiunilor fără corespondent și a cauzei diferenței."
                ),
                "proposed_owner": "TraceAI Control",
                "precondition": "Schema surselor confirmată pe primul caz real",
            }
        )

    result.conclusion_traceability.extend(
        [
            {
                "step": 1,
                "source": sources.stock_report.name,
                "key": product_code,
                "rule": "STOCK_REPORT_PRODUCT_FILTER",
                "result": f"diferență={result.initial_difference:.3f}",
                "evidence_level": "A",
            },
            {
                "step": 2,
                "source": sources.nomenclature.name,
                "key": product_code,
                "rule": "PRODUCT_MAPPING_WMS_WME",
                "result": f"{len(wme_ids)} identificator(i) WME",
                "evidence_level": "A" if len(wme_ids) == 1 else "C",
            },
            {
                "step": 3,
                "source": "WMS+WME+PRODUCTIE",
                "key": product_code,
                "rule": "PRODUCT_SOURCE_EXTRACTION",
                "result": (
                    f"WMS={len(wms_rows)}, WME={len(wme_rows)}, PROD={len(production_rows)}"
                ),
                "evidence_level": "A",
            },
        ]
    )

    return result


def investigation_to_dict(result: ProductInvestigationResult) -> dict[str, Any]:
    return asdict(result)
