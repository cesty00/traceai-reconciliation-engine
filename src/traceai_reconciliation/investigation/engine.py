from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

import pandas as pd

from .models import InvestigationSources, ProductInvestigationResult
from .production_matching import match_production_adjustments
from .delivery_matching import match_deliveries_and_returns
from .receipt_matching import match_inbound_receipts
from .special_status_matching import match_special_status_flow
from .production_input_matching import match_production_inputs
from .stock_correction_matching import match_generic_wms_stock_corrections
from .wme_residual_matching import match_wme_residual_movements
from .source_readers import (
    filter_by_period,
    first_non_empty,
    numeric_sum,
    parse_period,
    read_excel_table,
    read_filtered,
    read_production_product,
    read_wme_product,
    resolve_column,
    sha256_file,
)
from .source_hash_cache import hash_sources
from .source_index import SQLiteSourceIndex


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



def _wme_balance_total_at(
    wme_rows: pd.DataFrame,
    cutoff: pd.Timestamp,
    strictly_before: bool = False,
) -> tuple[dict[str, float], float | None]:
    if wme_rows.empty:
        return {}, None

    work = wme_rows.copy()
    work["Date"] = pd.to_datetime(work["Date"], errors="coerce", dayfirst=True)
    work["LineNo"] = pd.to_numeric(work["LineNo"], errors="coerce")
    work["Balance"] = pd.to_numeric(work["Balance"], errors="coerce")

    if strictly_before:
        work = work[work["Date"] < cutoff]
    else:
        work = work[work["Date"] <= cutoff]

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


def _wms_total_net_movement(
    wms_rows: pd.DataFrame,
) -> tuple[float | None, list[str]]:
    if wms_rows.empty:
        return 0.0, []

    op_col = resolve_column(wms_rows.columns, "operation_type")
    qty_col = resolve_column(wms_rows.columns, "quantity")
    quantities = pd.to_numeric(wms_rows[qty_col], errors="coerce").fillna(0.0)

    stock_effect_operations = {
        "Ajustare pozitiva",
        "Ajustare negativa",
        "Receptie",
        "Livrare",
    }
    internal_operations = {
        "Mutare",
        "Mutare intre gestiuni",
        "Incarcare Camion",
    }

    operations = wms_rows[op_col].astype(str).str.strip()
    unknown = sorted(
        {
            value
            for value in operations.unique().tolist()
            if value
            and value not in stock_effect_operations
            and value not in internal_operations
        }
    )
    if unknown:
        return None, unknown

    mask = operations.isin(stock_effect_operations)
    return float(quantities.loc[mask].sum()), []


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

    source_paths = {
        "stock_report": sources.stock_report,
        "opening_stock_wms": sources.opening_stock_wms,
        "wms_movements": sources.wms_movements,
        "wme_ledger": sources.wme_ledger,
        "production": sources.production,
        "nomenclature": sources.nomenclature,
    }
    result.source_hashes.update(
        hash_sources(source_paths, cache_dir=sources.cache_dir)
    )

    source_index = None
    if sources.use_source_index:
        if sources.cache_dir is None:
            raise ValueError(
                "use_source_index=True necesită cache_dir."
            )
        source_index = SQLiteSourceIndex(sources.cache_dir)
        index_rebuilt = source_index.ensure_index(
            sources.wms_movements,
            sources.wme_ledger,
            sources.production,
        )
        result.details["source_index"] = {
            "enabled": True,
            "rebuilt": index_rebuilt,
            "database": str(source_index.db_path),
        }
    else:
        result.details["source_index"] = {
            "enabled": False,
            "rebuilt": False,
        }

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

    if source_index is not None:
        wms_rows = source_index.read_wms_product(
            product_code,
            period=period,
        )
        production_rows = source_index.read_production_product(
            product_code,
            period=period,
        )
    else:
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

    if source_index is not None:
        wme_all_rows, wme_ids = source_index.read_wme_product(
            product_name,
            period=None,
        )
    else:
        wme_all_rows, wme_ids = read_wme_product(
            sources.wme_ledger,
            product_name,
            period=None,
        )
    wme_rows = filter_by_period(wme_all_rows, period)

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

    period_start, period_end = parse_period(period)

    opening_wme_by_warehouse, opening_wme_total = _wme_balance_total_at(
        wme_all_rows,
        period_start,
        strictly_before=True,
    )
    final_wme_by_warehouse, final_wme_total = _wme_balance_total_at(
        wme_all_rows,
        period_end + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
        strictly_before=False,
    )

    if opening_wme_total is not None:
        result.opening_stock_wme = round(opening_wme_total, decimals)

    wme_net_movement = (
        float(pd.to_numeric(wme_rows["SignedQuantity"], errors="coerce").fillna(0.0).sum())
        if not wme_rows.empty
        else 0.0
    )

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

    wms_net_movement, unknown_wms_operations = _wms_total_net_movement(wms_rows)
    if unknown_wms_operations:
        result.technical_warnings.append(
            "Reconstrucția totală WMS nu a fost calculată deoarece există tipuri de "
            f"operațiuni fără regulă de impact asupra stocului: {unknown_wms_operations}."
        )
    elif result.opening_stock_wms is not None and wms_net_movement is not None:
        result.calculated_stock_wms = round(
            result.opening_stock_wms + wms_net_movement,
            decimals,
        )
        wms_gap = round(
            (result.reported_stock_wms or 0.0) - result.calculated_stock_wms,
            decimals,
        )
        result.findings.append(
            {
                "type": "WMS_TOTAL_RECONSTRUCTION",
                "description": (
                    f"Stoc inițial WMS {result.opening_stock_wms:.3f} + "
                    f"mișcare netă cu impact extern {wms_net_movement:.3f} = "
                    f"stoc calculat {result.calculated_stock_wms:.3f}; "
                    f"QuantityWMS raportat este {(result.reported_stock_wms or 0.0):.3f}; "
                    f"abaterea este {wms_gap:.3f}."
                ),
                "evidence": "SRC-OPENING-WMS + SRC-WMS + SRC-STOCK-REPORT",
            }
        )

    if (
        result.opening_stock_wms is not None
        and result.opening_stock_wme is not None
        and wms_net_movement is not None
    ):
        initial_system_difference = round(
            result.opening_stock_wms - result.opening_stock_wme,
            decimals,
        )
        movement_system_difference = round(
            wms_net_movement - wme_net_movement,
            decimals,
        )
        reconstructed_difference = round(
            initial_system_difference + movement_system_difference,
            decimals,
        )
        result.findings.append(
            {
                "type": "DIFFERENCE_DECOMPOSITION",
                "description": (
                    f"Diferență la începutul perioadei: {initial_system_difference:.3f}; "
                    f"diferență generată de mișcările perioadei: "
                    f"{movement_system_difference:.3f}; total reconstruit: "
                    f"{reconstructed_difference:.3f}; diferență raportată: "
                    f"{result.initial_difference:.3f}."
                ),
                "evidence": "reconstrucție independentă WMS + WME",
            }
        )
    else:
        initial_system_difference = None
        movement_system_difference = None
        reconstructed_difference = None

    result.technical_warnings.append(
        "Reconstrucția WMS pe gestiuni/locații rămâne suspendată până la validarea "
        "mapării locațiilor WMS către gestiunile raportului. Reconstrucția totală pe "
        "produs folosește numai operațiunile cu impact total de stoc validate: "
        "Ajustare pozitiva, Ajustare negativa, Receptie și Livrare; Mutare/Mutare "
        "intre gestiuni nu modifică totalul produsului."
    )

    delivery_match = match_deliveries_and_returns(wms_rows, wme_rows)
    result.details["delivery_matching"] = {
        "wms_net_total": round(delivery_match.wms_net_total, decimals),
        "wme_ae_total": round(delivery_match.wme_ae_total, decimals),
        "residual_documents": len(delivery_match.residual_documents),
        "wme_only_documents": len(delivery_match.wme_only_documents),
        "residual_total": round(delivery_match.residual_total, decimals),
    }

    if delivery_match.wme_only_documents:
        for item in delivery_match.wme_only_documents:
            result.unmatched_operations.append(
                {
                    "date": "-",
                    "system": "WME",
                    "document": item["document"],
                    "operation_type": "AE_WME_ONLY",
                    "quantity": item["wme_ae_quantity"],
                    "reason": (
                        "AE WME fără document WMS candidat de livrare/retur "
                        "în perioada analizată"
                    ),
                    "status": item["status"],
                }
            )
        result.technical_warnings.append(
            f"{len(delivery_match.wme_only_documents)} documente AE WME-only "
            "au fost păstrate separat și nu modifică automat rezidualul "
            "DELIVERY."
        )

    if delivery_match.residual_documents:
        for item in delivery_match.residual_documents:
            result.unmatched_operations.append(
                {
                    "date": "-",
                    "system": "WMS↔WME",
                    "document": item["document"],
                    "operation_type": "DELIVERY_RETURN_NET_VS_AE",
                    "quantity": item["difference"],
                    "reason": (
                        f"WMS net {item['wms_net_quantity']:.3f} vs "
                        f"WME AE {item['wme_ae_quantity']:.3f}"
                    ),
                    "status": "QTY_DIFF",
                }
            )
        result.findings.append(
            {
                "type": "DELIVERY_RETURN_RESIDUAL",
                "description": (
                    f"După netarea Livrare + Receptie/retur WMS și compararea "
                    f"cu AE WME rămân {len(delivery_match.residual_documents)} "
                    f"documente cu diferență, total "
                    f"{delivery_match.residual_total:.3f} {result.unit}."
                ),
                "evidence": "SRC-WMS + SRC-WME(AE)",
            }
        )

    receipt_match = match_inbound_receipts(wms_rows, wme_rows)
    result.details["receipt_matching"] = {
        "supported_documents": len(receipt_match.documents),
        "residual_documents": len(receipt_match.residual_documents),
        "unsupported_receipts": len(receipt_match.unsupported_receipts),
        "wms_supported_total": round(
            receipt_match.wms_supported_total,
            decimals,
        ),
        "wme_supported_total": round(
            receipt_match.wme_supported_total,
            decimals,
        ),
        "residual_total": round(
            receipt_match.residual_total,
            decimals,
        ),
    }

    if receipt_match.documents:
        matched_count = sum(
            1 for item in receipt_match.documents
            if item["status"] == "MATCH"
        )
        result.findings.append(
            {
                "type": "INBOUND_RECEIPT_MATCHING",
                "description": (
                    f"Recepții inbound validate documentar: "
                    f"{matched_count}/{len(receipt_match.documents)} "
                    f"documente sunt concordante pentru familiile "
                    f"IN→FE și TRANSFER_CG→NT; rezidual total "
                    f"{receipt_match.residual_total:.3f} {result.unit}."
                ),
                "evidence": "SRC-WMS(Receptie) + SRC-WME(FE/NT)",
            }
        )

    if receipt_match.residual_documents:
        for item in receipt_match.residual_documents:
            result.unmatched_operations.append(
                {
                    "date": "-",
                    "system": "WMS↔WME",
                    "document": item["document"],
                    "operation_type": (
                        f"RECEIPT_{item['family']}_VS_"
                        f"{item['wme_operation_type']}"
                    ),
                    "quantity": item["difference"],
                    "reason": (
                        f"WMS {item['wms_quantity']:.3f} vs "
                        f"WME {item['wme_quantity']:.3f}"
                    ),
                    "status": "QTY_DIFF",
                }
            )

        result.technical_warnings.append(
            "Diferențele reziduale RECEIPT sunt raportate ca dovezi, "
            "dar nu sunt încă adăugate automat la diferența explicată "
            "până la validarea pe cazuri reale suplimentare."
        )

    if receipt_match.unsupported_receipts:
        result.technical_warnings.append(
            f"{len(receipt_match.unsupported_receipts)} recepții WMS aparțin "
            "familiilor neacoperite de matcherul inbound (de ex. retururi, "
            "TRANSFER_MOSE sau lanțuri -1/-2) și rămân în regulile dedicate."
        )

    production_input_match = match_production_inputs(wms_rows, wme_rows)
    result.details["production_input_matching"] = {
        "wms_total": round(production_input_match.wms_total, decimals),
        "wme_bc_total": round(production_input_match.wme_bc_total, decimals),
        "residual_documents": len(
            production_input_match.residual_documents
        ),
        "residual_total": round(
            production_input_match.residual_total,
            decimals,
        ),
    }

    if production_input_match.residual_documents:
        for item in production_input_match.residual_documents:
            result.unmatched_operations.append(
                {
                    "date": "-",
                    "system": "WMS↔WME",
                    "document": item["document"],
                    "operation_type": "PRODUCTION_IN_VS_BC",
                    "quantity": item["difference"],
                    "reason": (
                        f"WMS PRODUCTION-IN "
                        f"{item['wms_production_in']:.3f} vs "
                        f"WME BC {item['wme_bc']:.3f}"
                    ),
                    "status": "QTY_DIFF",
                }
            )
        result.findings.append(
            {
                "type": "PRODUCTION_INPUT_RESIDUAL",
                "description": (
                    f"PRODUCTION-IN WMS vs BC WME are "
                    f"{len(production_input_match.residual_documents)} "
                    f"documente cu diferență, total "
                    f"{production_input_match.residual_total:.3f} "
                    f"{result.unit}."
                ),
                "evidence": "SRC-WMS(PRODUCTION-IN) + SRC-WME(BC)",
            }
        )
    elif production_input_match.documents:
        result.findings.append(
            {
                "type": "PRODUCTION_INPUT_MATCH",
                "description": (
                    f"Toate cele "
                    f"{len(production_input_match.documents)} documente "
                    f"PRODUCTION-IN WMS sunt concordante cu BC WME; "
                    f"total WMS "
                    f"{production_input_match.wms_total:.3f} "
                    f"și total WME "
                    f"{production_input_match.wme_bc_total:.3f}."
                ),
                "evidence": "SRC-WMS(PRODUCTION-IN) + SRC-WME(BC)",
            }
        )

    production_match = match_production_adjustments(wms_rows, wme_rows)
    result.details["production_matching"] = {
        "wms_positive_total": round(production_match.wms_positive_total, decimals),
        "wme_np_total": round(production_match.wme_np_total, decimals),
        "reversal_pairs": len(production_match.reversal_pairs),
        "residual_adjustments": len(production_match.residual_wms_adjustments),
        "residual_total": round(production_match.residual_total, decimals),
    }

    if production_match.reversal_pairs:
        reversal_total = sum(
            item["quantity"] for item in production_match.reversal_pairs
        )
        result.findings.append(
            {
                "type": "WMS_PRODUCTION_REVERSAL_PAIRS",
                "description": (
                    f"Au fost identificate {len(production_match.reversal_pairs)} "
                    f"perechi WMS de ajustare pozitivă + ajustare negativă fără "
                    f"document, pe aceeași zi/locație/lot/cantitate, total "
                    f"{reversal_total:.3f} {result.unit}. Aceste perechi sunt "
                    "tratate ca reversări WMS și nu explică singure diferența finală."
                ),
                "evidence": "SRC-WMS + SRC-WME(NP)",
            }
        )

    if production_match.residual_wms_adjustments:
        for item in production_match.residual_wms_adjustments:
            result.unmatched_operations.append(
                {
                    "date": item["date"],
                    "system": "WMS",
                    "document": item["document"] or "-",
                    "operation_type": item["operation_type"],
                    "quantity": item["quantity"],
                    "reason": item["reason"],
                    "status": item["status"],
                }
            )

        residual_total = round(production_match.residual_total, decimals)
        result.findings.append(
            {
                "type": "WMS_ONLY_PRODUCTION_ADJUSTMENT",
                "description": (
                    f"Au rămas {len(production_match.residual_wms_adjustments)} "
                    f"ajustări negative WMS fără document și fără pereche de "
                    f"reversare, total {residual_total:.3f} {result.unit}. "
                    "Aceste operațiuni necesită validarea motivului operațional "
                    "și verificarea existenței unui corespondent WME."
                ),
                "evidence": "SRC-WMS + SRC-WME + matching producție",
            }
        )

        same_sign = (
            residual_total != 0
            and result.initial_difference != 0
            and (residual_total > 0) == (result.initial_difference > 0)
        )
        bounded = abs(residual_total) <= abs(result.initial_difference) + 10 ** (-decimals)
        if same_sign and bounded:
            result.explained_difference = residual_total
            result.unexplained_difference = round(
                result.initial_difference - residual_total,
                decimals,
            )
            result.cause_code = "CAUSE-WMS-ONLY-ADJUSTMENT-PARTIAL"
            result.cause_description = (
                "O parte din diferență este explicată de ajustări negative WMS "
                "fără document, fără pereche de reversare și fără corespondent "
                "WME identificat. Diferența reziduală rămâne în investigație."
            )
            result.cause_status = "PROBABILA"
            result.evidence_level = "B"
            result.verdict = "REVIEW"

    delivery_residual = round(delivery_match.residual_total, decimals)
    if (
        delivery_residual != 0
        and result.initial_difference != 0
        and (delivery_residual > 0) == (result.initial_difference > 0)
    ):
        candidate_explained = round(
            result.explained_difference + delivery_residual,
            decimals,
        )
        if abs(candidate_explained) <= abs(result.initial_difference) + 10 ** (-decimals):
            result.explained_difference = candidate_explained
            result.unexplained_difference = round(
                result.initial_difference - result.explained_difference,
                decimals,
            )
            if result.cause_code == "CAUSE-OPERATIONAL-MATCHING-PENDING":
                result.cause_code = "CAUSE-MULTI-PARTIAL"
            elif result.cause_code == "CAUSE-WMS-ONLY-ADJUSTMENT-PARTIAL":
                result.cause_code = "CAUSE-MULTI-PARTIAL"
            result.cause_description = (
                "Diferența este explicată parțial de operațiuni WMS fără "
                "corespondent și/sau diferențe cantitative reziduale după "
                "netarea documentelor de livrare/retur. Restul rămâne în investigație."
            )
            result.cause_status = "PROBABILA"
            result.evidence_level = "B"

    wme_residual_match = match_wme_residual_movements(
        wme_rows,
        excluded_warehouses={"DETERIORATE", "PROTAN", "MOSTRE"},
    )
    result.details["wme_residual_movements"] = {
        "residual_movements": len(
            wme_residual_match.residual_movements
        ),
        "wme_signed_total": round(
            wme_residual_match.wme_signed_total,
            decimals,
        ),
        "system_difference_effect": round(
            wme_residual_match.system_difference_effect,
            decimals,
        ),
    }

    if wme_residual_match.residual_movements:
        for item in wme_residual_match.residual_movements:
            result.unmatched_operations.append(
                {
                    "date": "-",
                    "system": "WME",
                    "document": item["document"],
                    "operation_type": item["operation_type"],
                    "quantity": item["system_difference_effect"],
                    "reason": (
                        f"Mișcare WME ne-standard în "
                        f"{item['warehouse']}; efect WMS-WME "
                        f"{item['system_difference_effect']:.3f}"
                    ),
                    "status": item["status"],
                }
            )
        result.findings.append(
            {
                "type": "WME_RESIDUAL_MOVEMENTS",
                "description": (
                    f"Mișcările WME non-standard în afara gestiunilor speciale "
                    f"au efect net asupra diferenței WMS-WME de "
                    f"{wme_residual_match.system_difference_effect:.3f} "
                    f"{result.unit}."
                ),
                "evidence": "SRC-WME(F/PV/alte tipuri ne-standard)",
            }
        )

        result.technical_warnings.append(
            "Mișcările WME non-standard sunt raportate ca dovezi reziduale, "
            "dar nu sunt adăugate automat la diferența explicată fără o "
            "legătură documentară validată."
        )

    special_status_match = match_special_status_flow(wms_rows, wme_rows)

    generic_correction_match = match_generic_wms_stock_corrections(
        wms_rows,
        excluded_locations={"INS.DET"},
    )
    result.details["generic_stock_corrections"] = {
        "residual_corrections": len(
            generic_correction_match.residual_corrections
        ),
        "residual_total": round(
            generic_correction_match.residual_total,
            decimals,
        ),
    }

    if generic_correction_match.residual_corrections:
        for item in generic_correction_match.residual_corrections:
            result.unmatched_operations.append(
                {
                    "date": item["date"],
                    "system": "WMS",
                    "document": item["document"] or "-",
                    "operation_type": "COR STOC",
                    "quantity": item["quantity"],
                    "reason": item["reason"],
                    "status": item["status"],
                }
            )
        result.findings.append(
            {
                "type": "GENERIC_WMS_STOCK_CORRECTION",
                "description": (
                    f"Au rămas "
                    f"{len(generic_correction_match.residual_corrections)} "
                    f"corecții WMS COR STOC fără document, în afara "
                    f"producției și fluxurilor speciale, total "
                    f"{generic_correction_match.residual_total:.3f} "
                    f"{result.unit}."
                ),
                "evidence": "SRC-WMS(COR STOC)",
            }
        )

        generic_residual = round(
            generic_correction_match.residual_total,
            decimals,
        )
        if (
            generic_residual != 0
            and result.initial_difference != 0
            and (generic_residual > 0)
            == (result.initial_difference > 0)
        ):
            candidate_explained = round(
                result.explained_difference + generic_residual,
                decimals,
            )
            pending_special = round(
                special_status_match.explained_total,
                decimals,
            )
            if (
                pending_special == 0
                or (pending_special > 0)
                != (result.initial_difference > 0)
            ):
                pending_special = 0.0

            if (
                abs(candidate_explained + pending_special)
                <= abs(result.initial_difference) + 10 ** (-decimals)
            ):
                result.explained_difference = candidate_explained
                result.unexplained_difference = round(
                    result.initial_difference
                    - result.explained_difference,
                    decimals,
                )
                result.cause_code = "CAUSE-MULTI-PARTIAL"
                result.cause_description = (
                    "Diferența este explicată parțial prin operațiuni WMS "
                    "fără corespondent și corecții de stoc reziduale. "
                    "Diferența de deschidere rămâne separată."
                )
                result.cause_status = "PROBABILA"
                result.evidence_level = "B"
                result.verdict = "REVIEW"

    result.details["special_status_matching"] = {
        "matched_groups": len(special_status_match.matched_groups),
        "residual_corrections": len(
            special_status_match.residual_wms_corrections
        ),
        "explained_total": round(
            special_status_match.explained_total,
            decimals,
        ),
    }

    if special_status_match.matched_groups:
        for group in special_status_match.matched_groups:
            result.findings.append(
                {
                    "type": "SPECIAL_STATUS_CANDIDATE_MATCH",
                    "description": (
                        f"Flux special candidat: WMS transfer "
                        f"{group['wms_transfer_total']:.3f} {result.unit} către "
                        f"{group['wms_destination']}, WME NT "
                        f"{group['wme_nt_total']:.3f} către "
                        f"{group['wme_warehouse']}, urmat de corecții "
                        f"WMS {group['wms_correction_total']:.3f}. "
                        "Corelarea este tratată drept cauză probabilă, nu regulă "
                        "generală activă."
                    ),
                    "evidence": "SRC-WMS + SRC-WME(NT) + SPECIAL_STATUS_CANDIDATE",
                }
            )

        special_residual = round(
            special_status_match.explained_total,
            decimals,
        )
        if (
            special_residual != 0
            and result.initial_difference != 0
            and (special_residual > 0)
            == (result.initial_difference > 0)
        ):
            candidate_explained = round(
                result.explained_difference + special_residual,
                decimals,
            )
            if (
                abs(candidate_explained)
                <= abs(result.initial_difference) + 10 ** (-decimals)
            ):
                result.explained_difference = candidate_explained
                result.unexplained_difference = round(
                    result.initial_difference
                    - result.explained_difference,
                    decimals,
                )
                result.cause_code = "CAUSE-MULTI-PARTIAL"
                result.cause_description = (
                    "Diferența este explicată parțial prin combinația dintre "
                    "ajustări WMS fără corespondent, diferențe reziduale după "
                    "netarea livrărilor/retururilor și un flux special candidat "
                    "INS.DET↔DETERIORATE. Diferența rămasă este păstrată separat."
                )
                result.cause_status = "PROBABILA"
                result.evidence_level = "B"
                result.verdict = "REVIEW"

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
            "wme_opening_balances": opening_wme_by_warehouse,
            "wme_final_balances": final_wme_by_warehouse,
            "wms_net_movement": wms_net_movement,
            "wme_net_movement": round(wme_net_movement, decimals),
            "initial_system_difference": initial_system_difference,
            "movement_system_difference": movement_system_difference,
            "reconstructed_difference": reconstructed_difference,
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
    elif result.explained_difference == 0:
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
                "Continuarea validării automate pentru familiile operaționale "
                "încă neacoperite sau rămase în REVIEW, cu promovarea regulilor "
                "candidate numai după confirmare pe cazuri reale independente."
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
