from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

import pandas as pd

from .models import InvestigationSources, ProductInvestigationResult
from .source_readers import (
    filter_by_period,
    first_non_empty,
    numeric_sum,
    read_excel_table,
    read_filtered,
    read_production_product,
    read_wme_product,
    resolve_column,
    sha256_file,
)


def _row_value(
    row: pd.Series,
    columns: pd.Index,
    semantic: str,
    default: Any = "-",
) -> Any:
    column = resolve_column(columns, semantic, required=False)
    if column is None:
        return default
    value = row.get(column, default)
    if pd.isna(value):
        return default
    return value


def _timeline_from_wms(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        entries.append(
            {
                "date": _row_value(row, df.columns, "date"),
                "system": "WMS",
                "document": _row_value(row, df.columns, "document"),
                "operation_type": _row_value(row, df.columns, "operation_type"),
                "quantity": _row_value(row, df.columns, "quantity"),
                "warehouse": _row_value(row, df.columns, "warehouse"),
                "counterpart": "-",
                "verdict": "REVIEW",
                "note": "Operațiune WMS extrasă automat pentru produs.",
            }
        )
    return entries


def _timeline_from_wme(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        entries.append(
            {
                "date": row.get("Date", "-"),
                "system": "WME",
                "document": row.get("Document", "-"),
                "operation_type": row.get("OperationType", "-"),
                "quantity": row.get("SignedQuantity", "-"),
                "warehouse": row.get("Warehouse", "-"),
                "counterpart": row.get("Partner", "-"),
                "verdict": "REVIEW",
                "note": f"Sold după operațiune: {row.get('Balance', '-')}",
            }
        )
    return entries


def _timeline_from_production(
    df: pd.DataFrame,
    product_code: str,
) -> list[dict[str, Any]]:
    if df.empty:
        return []

    entries: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        kind = str(row.get("TipLinie", "")).strip().upper()
        if kind == "PREDARE":
            code = str(row.get("PRE_Cod Articol", "")).strip()
            if code != str(product_code).strip():
                continue
            qty = row.get("PRE_Cantitate Predare", "-")
            unit = row.get("PRE_U.M.", "-")
        elif kind == "CONSUM":
            code = str(row.get("CON_Cod Articol", "")).strip()
            if code != str(product_code).strip():
                continue
            qty = row.get("CON_Cantitate Consumata", "-")
            unit = row.get("CON_U.M.", "-")
        else:
            continue

        entries.append(
            {
                "date": row.get("Data Start", "-"),
                "system": "PRODUCTIE",
                "document": row.get("Numar Comanda", "-"),
                "operation_type": kind,
                "quantity": qty,
                "warehouse": row.get("Utilaj Productie", "-"),
                "counterpart": "-",
                "verdict": "REVIEW",
                "note": f"UM producție: {unit}",
            }
        )
    return entries


def _validate_nomenclature(
    nomenclature: pd.DataFrame,
    product_code: str,
    product_name: str,
) -> tuple[str, str]:
    if nomenclature.empty:
        return "ABSENT", "D"

    code_col = resolve_column(nomenclature.columns, "wms_product_code", required=False)
    name_col = resolve_column(nomenclature.columns, "product_name", required=False)
    if code_col is None:
        return "ABSENT", "D"

    rows = nomenclature[
        nomenclature[code_col].astype(str).str.strip() == str(product_code).strip()
    ].copy()
    if rows.empty:
        return "COD_LIPSA", "C"

    if name_col is None:
        return "COD_CONFIRMAT", "B"

    names = {
        str(value).strip()
        for value in rows[name_col].dropna().tolist()
        if str(value).strip()
    }
    if product_name in names and len(names) == 1:
        return "COD_SI_DENUMIRE_CONFIRMATE", "A"
    if product_name in names:
        return "COD_CONFIRMAT_DENUMIRE_AMBIGUA", "B"
    return "COD_CONFIRMAT_DENUMIRE_DIFERITA", "C"


def _wme_final_balances(wme_rows: pd.DataFrame) -> tuple[dict[str, float], float | None]:
    if wme_rows.empty:
        return {}, None

    work = wme_rows.copy()
    work["Date"] = pd.to_datetime(work["Date"], errors="coerce", dayfirst=True)
    work["LineNo"] = pd.to_numeric(work["LineNo"], errors="coerce")
    work["Balance"] = pd.to_numeric(work["Balance"], errors="coerce")

    final_by_warehouse: dict[str, float] = {}
    for warehouse, group in work.groupby("Warehouse", dropna=False):
        ordered = group.sort_values(["Date", "LineNo"], na_position="first")
        balances = ordered["Balance"].dropna()
        if balances.empty:
            continue
        final_by_warehouse[str(warehouse)] = float(balances.iloc[-1])

    if not final_by_warehouse:
        return {}, None
    return final_by_warehouse, float(sum(final_by_warehouse.values()))


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
        stock_report[stock_code_col].astype(str).str.strip()
        == str(product_code).strip()
    ].copy()
    if stock_rows.empty:
        raise KeyError(f"Produsul {product_code} nu există în raportul de stoc.")

    product_name = first_non_empty(stock_rows, "product_name") or product_code
    reported_wms = numeric_sum(stock_rows, "stock_wms")
    reported_wme = numeric_sum(stock_rows, "stock_wme")
    initial_difference = numeric_sum(stock_rows, "stock_difference")

    result = ProductInvestigationResult(
        case_id=case_id,
        product_code=product_code,
        product_name=product_name,
        unit="UM",
        period=period,
        report_date=report_date,
        initial_difference=round(initial_difference, decimals),
        reported_stock_wms=round(reported_wms, decimals),
        reported_stock_wme=round(reported_wme, decimals),
        unexplained_difference=round(initial_difference, decimals),
    )

    result.sources_used.extend(
        [
            {
                "source_id": "SRC-STOCK-REPORT",
                "name": sources.stock_report.name,
                "period": period,
                "role": "diferență de pornire",
                "status": "VERIFICAT",
            },
            {
                "source_id": "SRC-OPENING-WMS",
                "name": sources.opening_stock_wms.name,
                "period": "01.01.2026",
                "role": "stoc inițial WMS",
                "status": "VERIFICAT",
            },
            {
                "source_id": "SRC-WMS",
                "name": sources.wms_movements.name,
                "period": period,
                "role": "mișcări WMS",
                "status": "VERIFICAT",
            },
            {
                "source_id": "SRC-WME",
                "name": sources.wme_ledger.name,
                "period": period,
                "role": "fișă magazie WME",
                "status": "VERIFICAT",
            },
            {
                "source_id": "SRC-PROD",
                "name": sources.production.name,
                "period": period,
                "role": "producție",
                "status": "VERIFICAT",
            },
            {
                "source_id": "SRC-NOM",
                "name": sources.nomenclature.name,
                "period": "-",
                "role": "nomenclator produs",
                "status": "VERIFICAT",
            },
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

    opening_rows = read_filtered(
        sources.opening_stock_wms,
        "product_code",
        [product_code],
    )
    if opening_rows.empty:
        result.technical_warnings.append(
            f"Produsul {product_code} nu a fost găsit în stocul inițial WMS."
        )
    else:
        result.opening_stock_wms = round(
            numeric_sum(opening_rows, "initial_stock"),
            decimals,
        )

    wms_rows = read_filtered(
        sources.wms_movements,
        "product_code",
        [product_code],
    )
    wms_rows = filter_by_period(wms_rows, period)

    production_rows = read_production_product(
        sources.production,
        product_code,
        period=period,
    )

    nomenclature = read_excel_table(sources.nomenclature)
    nomenclature_status, nomenclature_evidence = _validate_nomenclature(
        nomenclature,
        product_code,
        product_name,
    )

    wme_rows, wme_ids = read_wme_product(
        sources.wme_ledger,
        product_name,
        period=period,
    )

    if not wms_rows.empty:
        unit = first_non_empty(wms_rows, "unit")
        if unit:
            result.unit = unit
    if result.unit == "UM" and not wme_rows.empty:
        wme_units = [
            str(value).strip()
            for value in wme_rows["Unit"].dropna().tolist()
            if str(value).strip()
        ]
        if wme_units:
            result.unit = wme_units[0]

    if not wme_ids:
        result.technical_warnings.append(
            f"Denumirea exactă '{product_name}' nu a fost găsită în fișa WME."
        )
    elif len(wme_ids) > 1:
        result.technical_warnings.append(
            f"Denumirea exactă '{product_name}' este asociată cu mai multe ID-uri WME: "
            f"{sorted(wme_ids)}."
        )
    elif nomenclature_status == "COD_LIPSA":
        result.technical_warnings.append(
            f"Codul {product_code} lipsește din nomenclatorul încărcat. "
            f"Extragerea WME folosește denumirea exactă din raportul de stoc, "
            f"care conduce univoc la ID WME {next(iter(wme_ids))}. "
            "Maparea rămâne de validat înainte să devină regulă generală."
        )

    final_wme_by_warehouse, final_wme_total = _wme_final_balances(wme_rows)
    if final_wme_total is not None:
        result.calculated_stock_wme = round(final_wme_total, decimals)
        wme_gap = round(
            (result.reported_stock_wme or 0.0) - result.calculated_stock_wme,
            decimals,
        )
        result.findings.append(
            {
                "type": "WME_BALANCE_CHECK",
                "description": (
                    f"Soldurile finale WME pe gestiuni însumează "
                    f"{result.calculated_stock_wme:.3f} {result.unit}; "
                    f"QuantityERP din raport este {(result.reported_stock_wme or 0.0):.3f}; "
                    f"abaterea este {wme_gap:.3f}."
                ),
                "evidence": "SRC-WME + SRC-STOCK-REPORT",
            }
        )

    result.technical_warnings.append(
        "Reconstrucția cantitativă WMS pe gestiuni rămâne suspendată până la "
        "validarea mapării locațiilor WMS către gestiunile raportului și a semnului "
        "fiecărui tip de operațiune. Rândurile WMS sunt însă extrase și delimitate "
        "strict la perioada cazului."
    )

    result.operation_timeline.extend(_timeline_from_wms(wms_rows))
    result.operation_timeline.extend(_timeline_from_wme(wme_rows))
    result.operation_timeline.extend(
        _timeline_from_production(production_rows, product_code)
    )
    result.operation_timeline.sort(key=lambda item: str(item.get("date", "")))

    result.details.update(
        {
            "stock_report_rows": len(stock_rows),
            "wms_rows": len(wms_rows),
            "wme_rows": len(wme_rows),
            "production_rows": len(production_rows),
            "wme_mapping_ids": sorted(wme_ids),
            "nomenclature_status": nomenclature_status,
            "nomenclature_evidence": nomenclature_evidence,
            "wme_final_balances": final_wme_by_warehouse,
        }
    )

    result.findings.append(
        {
            "type": "SOURCE_COUNTS",
            "description": (
                f"Rânduri relevante în perioada analizată: "
                f"WMS={len(wms_rows)}, WME={len(wme_rows)}, "
                f"producție={len(production_rows)}."
            ),
            "evidence": "filtrare automată pe produs și perioadă",
        }
    )

    if final_wme_total is not None:
        result.findings.append(
            {
                "type": "WME_FINAL_BY_WAREHOUSE",
                "description": "; ".join(
                    f"{warehouse}={quantity:.3f}"
                    for warehouse, quantity in sorted(final_wme_by_warehouse.items())
                ),
                "evidence": "ultimul sold WME per gestiune în perioada analizată",
            }
        )

    if not wme_ids:
        result.cause_code = "CAUSE-MASTER-DATA"
        result.cause_description = (
            "Produsul nu poate fi legat în siguranță de fișa WME pe baza "
            "dovezilor disponibile."
        )
        result.cause_status = "PROBABILA"
        result.evidence_level = "C"
    elif len(wme_ids) > 1:
        result.cause_code = "CAUSE-MASTER-DATA"
        result.cause_description = (
            "Denumirea produsului este asociată cu mai multe ID-uri interne WME."
        )
        result.cause_status = "PROBABILA"
        result.evidence_level = "C"
    elif abs(result.initial_difference) <= 10 ** (-decimals):
        result.verdict = "MATCH_DIRECT"
        result.evidence_level = "A"
        result.cause_code = "CAUSE-NONE"
        result.cause_description = (
            "Raportul de stoc nu indică diferență materială pentru produs."
        )
        result.cause_status = "CONFIRMATA"
        result.explained_difference = 0.0
        result.unexplained_difference = 0.0
    else:
        result.verdict = "REVIEW"
        result.evidence_level = "B" if len(wme_ids) == 1 else "C"
        result.cause_code = "CAUSE-OPERATIONAL-MATCHING-PENDING"
        result.cause_description = (
            "Diferența este confirmată între soldul WMS raportat și soldul WME "
            "reconstruit, dar cauza operațională necesită matching document cu "
            "document între WMS și WME."
        )
        result.cause_status = "NEDETERMINATA"

    result.recommendations.append(
        {
            "priority": "P1",
            "action_type": "IMEDIATA",
            "recommendation": (
                "Compararea document cu document a operațiunilor WMS și WME "
                "extrase pentru produs înaintea oricărei ajustări de stoc."
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
                "Activarea următorului strat v0.3: matching operațional "
                "WMS↔WME pentru RECEIPT / DELIVERY / RETURN_IN / TRANSFER / "
                "PRODUCTION și identificarea diferenței explicate."
            ),
            "proposed_owner": "TraceAI Control",
            "precondition": "Maparea locațiilor și regulile de semn validate",
        }
    )

    mapping_result = (
        f"ID WME unic {next(iter(wme_ids))}"
        if len(wme_ids) == 1
        else f"{len(wme_ids)} ID-uri WME"
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
                "source": sources.wme_ledger.name,
                "key": product_name,
                "rule": "WME_EXACT_NAME_TO_INTERNAL_ID",
                "result": mapping_result,
                "evidence_level": "B" if nomenclature_status == "COD_LIPSA" else "A",
            },
            {
                "step": 3,
                "source": "WMS+WME+PRODUCTIE",
                "key": product_code,
                "rule": "PRODUCT_AND_PERIOD_SOURCE_EXTRACTION",
                "result": (
                    f"WMS={len(wms_rows)}, WME={len(wme_rows)}, "
                    f"PROD={len(production_rows)}"
                ),
                "evidence_level": "A",
            },
            {
                "step": 4,
                "source": sources.wme_ledger.name,
                "key": product_code,
                "rule": "WME_FINAL_BALANCE_BY_WAREHOUSE",
                "result": (
                    f"WME calculat={result.calculated_stock_wme}"
                    if result.calculated_stock_wme is not None
                    else "sold WME indisponibil"
                ),
                "evidence_level": "A",
            },
        ]
    )

    return result


def investigation_to_dict(
    result: ProductInvestigationResult,
) -> dict[str, Any]:
    return asdict(result)
