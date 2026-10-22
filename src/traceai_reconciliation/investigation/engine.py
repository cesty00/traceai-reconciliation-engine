from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

import pandas as pd

from .models import InvestigationSources, ProductInvestigationResult
from .nomenclature_validation import validate_nomenclature
from .opening_stock_policy import resolve_opening_stock_wms
from .product_identity import resolve_product_identity
from .operation_timeline import (
    timeline_from_production,
    timeline_from_wme,
    timeline_from_wms,
)
from .auto_explain import (
    auto_explanation_from_investigation,
    auto_explanation_to_dict,
)
from .production_matching import match_production_adjustments
from .delivery_matching import match_deliveries_and_returns
from .receipt_matching import match_inbound_receipts
from .special_status_matching import match_special_status_flow
from .production_input_matching import match_production_inputs
from .stock_correction_matching import match_generic_wms_stock_corrections
from .stock_report_zone_matching import (
    has_offsetting_zone_differences,
    reconcile_stock_report_zones,
)
from .transfer_mose_matching import (
    match_transfer_mose,
    match_transfer_mose_baskets,
)
from .wme_residual_matching import match_wme_residual_movements
from .inventory_adjustment_matching import match_inventory_adjustments
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
from .stock_balance import (
    wme_balance_total_at,
    wme_final_balances,
    wms_total_net_movement,
)

# Backward-compatible private aliases kept during incremental refactoring.
_wme_balance_total_at = wme_balance_total_at
_wme_final_balances = wme_final_balances
_wms_total_net_movement = wms_total_net_movement
from .source_provenance import source_paths, source_usage
from .source_hash_cache import hash_sources
from .source_index_policy import resolve_source_index


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
        source_usage(sources, period=period)
    )
    result.source_hashes.update(
        hash_sources(
            source_paths(sources),
            cache_dir=sources.cache_dir,
        )
    )

    source_index_resolution = resolve_source_index(sources)
    source_index = source_index_resolution.index
    result.details["source_index"] = source_index_resolution.details

    opening_resolution = resolve_opening_stock_wms(
        sources,
        product_code=product_code,
        decimals=decimals,
    )
    result.opening_stock_wms = opening_resolution.value
    if opening_resolution.warning:
        result.technical_warnings.append(opening_resolution.warning)
    result.details["opening_stock_policy"] = opening_resolution.details

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
    nomenclature_status, nomenclature_evidence = validate_nomenclature(
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

    identity_resolution = resolve_product_identity(
        current_unit=result.unit,
        wms_rows=wms_rows,
        wme_rows=wme_rows,
        wme_ids=wme_ids,
        product_code=product_code,
        product_name=product_name,
        nomenclature_status=nomenclature_status,
    )
    result.unit = identity_resolution.unit
    result.technical_warnings.extend(identity_resolution.warnings)

    period_start, period_end = parse_period(period)

    opening_wme_by_warehouse, opening_wme_total = wme_balance_total_at(
        wme_all_rows,
        period_start,
        strictly_before=True,
    )
    final_wme_by_warehouse, final_wme_total = wme_balance_total_at(
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

    wms_net_movement, unknown_wms_operations = wms_total_net_movement(wms_rows)
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

    stock_zone_match = reconcile_stock_report_zones(
        stock_rows,
        final_wme_by_warehouse,
    )
    result.details["stock_report_zone_matching"] = {
        "rows": stock_zone_match.rows,
        "confirmed_report_mapping_rows": len(
            stock_zone_match.confirmed_report_mapping_rows
        ),
        "unresolved_rows": len(stock_zone_match.unresolved_rows),
        "mapping_effect_total": round(
            stock_zone_match.mapping_effect_total,
            decimals,
        ),
        "applied_to_explanation": bool(
            stock_zone_match.confirmed_report_mapping_rows
        ),
    }

    if stock_zone_match.confirmed_report_mapping_rows:
        mapping_effect = round(
            stock_zone_match.mapping_effect_total,
            decimals,
        )
        result.explained_difference = round(
            result.explained_difference + mapping_effect,
            decimals,
        )
        result.unexplained_difference = round(
            result.initial_difference - result.explained_difference,
            decimals,
        )
        result.findings.append(
            {
                "type": "STOCK_REPORT_ERP_ZERO_MAPPING",
                "description": (
                    f"{len(stock_zone_match.confirmed_report_mapping_rows)} "
                    f"rânduri de raport cu QuantityERP=0 au fost confirmate ca "
                    f"artefacte de mapare deoarece soldul WMS este egal cu "
                    f"soldul WME. Efect total asupra diferenței raportate: "
                    f"{mapping_effect:.3f} {result.unit}."
                ),
                "evidence": "SRC-STOCK-REPORT + SRC-WME + GST-02/GST-03",
            }
        )
        result.cause_code = "CAUSE-REPORT-MAPPING-PARTIAL"
        result.cause_description = (
            "O parte din diferența raportată provine din logica de mapare a "
            "raportului: QuantityERP=0 pentru o gestiune în care WMS și WME "
            "au același sold. Restul diferenței se investighează operațional."
        )
        result.cause_status = "CONFIRMATA"
        result.evidence_level = "A"
        result.verdict = "REVIEW"

    if stock_zone_match.unresolved_rows:
        result.technical_warnings.append(
            f"{len(stock_zone_match.unresolved_rows)} rânduri de gestiune din "
            "raport nu au putut fi validate automat față de soldurile WME și "
            "rămân REVIEW."
        )

    offsetting_zone_differences = has_offsetting_zone_differences(
        stock_zone_match,
        total_difference=result.initial_difference,
        tolerance=10 ** (-decimals),
    )
    if offsetting_zone_differences:
        material_rows = [
            row
            for row in stock_zone_match.rows
            if abs(float(row.get("report_difference") or 0.0))
            > 10 ** (-decimals)
        ]
        result.findings.append(
            {
                "type": "STOCK_REPORT_OFFSETTING_ZONE_DIFFERENCES",
                "description": (
                    "Diferența totală pe produs este zero, dar raportul conține "
                    f"{len(material_rows)} rânduri de gestiune cu diferențe "
                    "materiale care se compensează între ele. Cazul nu poate fi "
                    "închis ca MATCH_DIRECT până la validarea mapării/locației."
                ),
                "evidence": "SRC-STOCK-REPORT + STOCK_REPORT_ZONE_MATCHING",
            }
        )

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
        "derived_receipt_documents": (
            delivery_match.derived_receipt_documents
        ),
        "net_zero_derived_documents": (
            delivery_match.net_zero_derived_documents
        ),
        "residual_total": round(delivery_match.residual_total, decimals),
        "applied_to_explanation": False,
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

    has_transfer_mose = False
    if "Numar comanda" in wms_rows.columns:
        has_transfer_mose = (
            wms_rows["Numar comanda"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.startswith("TRANSFER_MOSE")
            .any()
        )

    transfer_mose_scope = "PRODUCT_FALLBACK"
    if source_index is not None and has_transfer_mose:
        transfer_mose_match = match_transfer_mose_baskets(
            source_index.read_wms_transfer_mose(period=period),
            source_index.read_wme_mose_nt(period=period),
            product_name=product_name,
        )
        transfer_mose_scope = "BASKET_INDEXED"
    else:
        transfer_mose_match = match_transfer_mose(
            wms_rows,
            wme_rows,
        )

    result.details["transfer_mose_matching"] = {
        "scope": transfer_mose_scope,
        "matches": len(transfer_mose_match.matches),
        "cancelled_orders": len(
            transfer_mose_match.cancelled_orders
        ),
        "residual_wms_transfers": len(
            transfer_mose_match.residual_wms_transfers
        ),
        "wme_only_nt": len(
            transfer_mose_match.wme_only_nt
        ),
        "matched_wms_total": round(
            transfer_mose_match.matched_wms_total,
            decimals,
        ),
        "residual_wms_total": round(
            transfer_mose_match.residual_wms_total,
            decimals,
        ),
    }

    if transfer_mose_match.matches:
        result.findings.append(
            {
                "type": "TRANSFER_MOSE_MATCHING",
                "description": (
                    f"TRANSFER_MOSE: "
                    f"{len(transfer_mose_match.matches)} transferuri WMS "
                    f"au corespondent NT WME; "
                    f"{len(transfer_mose_match.cancelled_orders)} ordine "
                    f"au fost anulate complet după netarea _DEL_. "
                    "Transferurile sunt tratate ca flux intern și nu modifică "
                    "automat diferența totală WMS-WME."
                ),
                "evidence": "SRC-WMS(TRANSFER_MOSE) + SRC-WME(NT)",
            }
        )

    for item in transfer_mose_match.residual_wms_transfers:
        result.unmatched_operations.append(
            {
                "date": (
                    str(item.get("first_date"))
                    if item.get("first_date") is not None
                    else "-"
                ),
                "system": "WMS↔WME",
                "document": item.get("order", "-"),
                "operation_type": "TRANSFER_MOSE_VS_NT",
                "quantity": item.get("net_quantity", 0.0),
                "reason": (
                    f"TRANSFER_MOSE fără corespondent NT univoc; "
                    f"status={item.get('status', 'REVIEW')}; "
                    f"Document intrare={item.get('document_in', [])}; "
                    f"Document comanda={item.get('document_order', [])}."
                ),
                "status": item.get("status", "REVIEW"),
            }
        )

    for item in transfer_mose_match.wme_only_nt:
        result.unmatched_operations.append(
            {
                "date": (
                    str(item.get("date"))
                    if item.get("date") is not None
                    else "-"
                ),
                "system": "WME",
                "document": item.get("document", "-"),
                "operation_type": "NT_MOSE_WME_ONLY",
                "quantity": item.get("signed_quantity", 0.0),
                "reason": (
                    "NT WME între MOSE și DEPOZIT PRINCIPAL fără "
                    "TRANSFER_MOSE WMS univoc identificat."
                ),
                "status": item.get("status", "WME_ONLY_NT_REVIEW"),
            }
        )

    if (
        transfer_mose_match.residual_wms_transfers
        or transfer_mose_match.wme_only_nt
    ):
        result.technical_warnings.append(
            "Excepțiile TRANSFER_MOSE/NT rămân REVIEW; matcherul nu forțează "
            "corespondenta pe simpla coincidență de cantitate."
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

    production_input_match = match_production_inputs(
        wms_rows,
        wme_rows,
        production_rows=production_rows,
    )
    production_input_confirmed_missing = [
        item
        for item in production_input_match.residual_documents
        if item.get("residual_kind") == "WME_BC_MISSING"
        and item.get("production_confirmed", False)
    ]
    production_input_whole_document_missing = 0
    if source_index is not None:
        for item in production_input_confirmed_missing:
            global_bc_rows = source_index.count_wme_operation_document(
                "BC",
                str(item["document"]),
            )
            item["global_wme_bc_rows"] = global_bc_rows
            item["document_event"] = (
                "WHOLE_BC_DOCUMENT_MISSING"
                if global_bc_rows == 0
                else "PRODUCT_BC_LINE_MISSING"
            )
            if global_bc_rows == 0:
                production_input_whole_document_missing += 1
    result.details["production_input_matching"] = {
        "wms_total": round(production_input_match.wms_total, decimals),
        "wms_reversal_total": round(
            production_input_match.wms_reversal_total,
            decimals,
        ),
        "wms_effective_total": round(
            production_input_match.wms_effective_total,
            decimals,
        ),
        "wme_bc_total": round(production_input_match.wme_bc_total, decimals),
        "reversed_documents": len(
            production_input_match.reversed_documents or []
        ),
        "residual_documents": len(
            production_input_match.residual_documents
        ),
        "production_confirmed_missing_bc": len(
            production_input_confirmed_missing
        ),
        "whole_bc_document_missing": (
            production_input_whole_document_missing
            if source_index is not None
            else None
        ),
        "global_document_check_performed": source_index is not None,
        "residual_total": round(
            production_input_match.residual_total,
            decimals,
        ),
        "persistent_residual_total": round(
            production_input_match.persistent_residual_total,
            decimals,
        ),
        "persistent_residual_documents": (
            production_input_match.persistent_residual_documents or []
        ),
        "neutralized_residual_documents": (
            production_input_match.neutralized_residual_documents or []
        ),
        "basket_groups": production_input_match.basket_groups or [],
        "inventory_checkpoint_date": (
            production_input_match.inventory_checkpoint_date
        ),
        "safe_to_auto_explain": (
            production_input_match.safe_to_auto_explain
        ),
        "applied_to_explanation": False,
    }

    if production_input_match.reversed_documents:
        reversed_total = sum(
            abs(float(item["wms_production_in"]))
            for item in production_input_match.reversed_documents
        )
        result.findings.append(
            {
                "type": "PRODUCTION_INPUT_WMS_REVERSAL",
                "description": (
                    f"{len(production_input_match.reversed_documents)} "
                    f"documente PRODUCTION-IN au fost reversate explicit in "
                    f"WMS prin COR STOC cu referinta la aceeasi comanda, total "
                    f"{reversed_total:.3f} {result.unit}. Aceste documente nu "
                    f"sunt tratate ca BC lipsa si nu pot explica automat "
                    f"diferenta fata de WME."
                ),
                "evidence": "SRC-WMS(PRODUCTION-IN + COR STOC) + PROD-05",
            }
        )

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
                        f"WME BC {item['wme_bc']:.3f}; "
                        f"producție {item.get('production_consumption', 0.0):.3f}; "
                        f"tip={item.get('residual_kind', 'QTY_DIFF')}; "
                        f"eveniment={item.get('document_event', 'NEVERIFICAT_GLOBAL')}"
                    ),
                    "status": "QTY_DIFF",
                }
            )
        if source_index is not None and production_input_confirmed_missing:
            result.findings.append(
                {
                    "type": "PRODUCTION_INPUT_DOCUMENT_EVENT",
                    "description": (
                        f"Dintre {len(production_input_confirmed_missing)} "
                        f"documente BC lipsă pentru produs, "
                        f"{production_input_whole_document_missing} au 0 rânduri "
                        f"BC la nivel global în WME. Verificarea globală este "
                        f"doar evidență de cauză și nu închide automat cazul."
                    ),
                    "evidence": "SRC-WME global OperationType=BC + PROD-04",
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
                    f"{result.unit}; "
                    f"{len(production_input_confirmed_missing)} documente "
                    f"au consumul WMS confirmat exact de raportul de producție "
                    f"și BC WME lipsă."
                ),
                "evidence": (
                    "SRC-WMS(PRODUCTION-IN) + SRC-WME(BC) + SRC-PROD(CONSUM)"
                ),
            }
        )
    elif production_input_match.documents:
        active_documents = (
            len(production_input_match.documents)
            - len(production_input_match.reversed_documents or [])
        )
        result.findings.append(
            {
                "type": "PRODUCTION_INPUT_MATCH",
                "description": (
                    f"După excluderea a "
                    f"{len(production_input_match.reversed_documents or [])} "
                    f"documente PRODUCTION-IN reversate explicit în WMS, "
                    f"cele {active_documents} documente active sunt "
                    f"concordante cu BC WME; total WMS efectiv "
                    f"{production_input_match.wms_effective_total:.3f} "
                    f"și total WME "
                    f"{production_input_match.wme_bc_total:.3f}."
                ),
                "evidence": (
                    "SRC-WMS(PRODUCTION-IN + COR STOC) + SRC-WME(BC)"
                ),
            }
        )

    production_match = match_production_adjustments(wms_rows, wme_rows)
    result.details["production_matching"] = {
        "wms_positive_total": round(production_match.wms_positive_total, decimals),
        "wme_np_total": round(production_match.wme_np_total, decimals),
        "reversal_pairs": len(production_match.reversal_pairs),
        "residual_adjustments": len(production_match.residual_wms_adjustments),
        "residual_total": round(production_match.residual_total, decimals),
        "document_residuals": production_match.document_residuals,
        "document_residual_total": round(
            production_match.document_residual_total,
            decimals,
        ),
        "residual_adjustment_items": (
            production_match.residual_wms_adjustments
        ),
        "unconsumed_correction_items": (
            production_match.unconsumed_correction_items
        ),
        "unconsumed_correction_total": round(
            production_match.unconsumed_correction_total,
            decimals,
        ),
        "applied_to_explanation": False,
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
            result.details["production_matching"][
                "applied_to_explanation"
            ] = True
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

    production_input_residual = round(
        production_input_match.residual_total,
        decimals,
    )
    production_input_safe = (
        bool(production_input_match.residual_documents)
        and len(production_input_confirmed_missing)
        == len(production_input_match.residual_documents)
        and all(
            item.get("residual_kind") == "WME_BC_MISSING"
            for item in production_input_match.residual_documents
        )
    )
    if production_input_safe and production_input_residual != 0:
        candidate_explained = round(
            result.explained_difference + production_input_residual,
            decimals,
        )
        if abs(candidate_explained - result.initial_difference) <= 10 ** (-decimals):
            had_previous_explanation = abs(result.explained_difference) > 10 ** (-decimals)
            result.explained_difference = candidate_explained
            result.unexplained_difference = round(
                result.initial_difference - result.explained_difference,
                decimals,
            )
            result.details["production_input_matching"][
                "applied_to_explanation"
            ] = True
            result.cause_code = (
                "CAUSE-MULTI-PARTIAL"
                if had_previous_explanation
                else "CAUSE-WME-BC-MISSING-CONFIRMED"
            )
            result.cause_description = (
                "Diferența este explicată integral de consumuri PRODUCTION-IN "
                "înregistrate în WMS și confirmate exact de raportul de "
                "producție, pentru care documentele BC corespondente lipsesc "
                "din WME."
            )
            result.cause_status = "CONFIRMATA"
            result.evidence_level = "A"
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
            previous_cause_code = result.cause_code
            result.explained_difference = candidate_explained
            result.details["delivery_matching"][
                "applied_to_explanation"
            ] = True
            result.unexplained_difference = round(
                result.initial_difference - result.explained_difference,
                decimals,
            )
            result.cause_code = "CAUSE-MULTI-PARTIAL"
            if previous_cause_code == "CAUSE-REPORT-MAPPING-PARTIAL":
                result.cause_description = (
                    "Diferența este explicată prin combinația dintre un efect "
                    "confirmat de mapare al raportului de stoc și o diferență "
                    "reziduală de livrare/retur WMS față de AE WME."
                )
            elif abs(result.unexplained_difference) <= 10 ** (-decimals):
                result.cause_description = (
                    "Diferența este explicată integral prin combinația "
                    "componentelor operaționale validate și a diferențelor "
                    "reziduale după netarea documentelor de livrare/retur."
                )
            else:
                result.cause_description = (
                    "Diferența este explicată parțial de operațiuni WMS fără "
                    "corespondent și/sau diferențe cantitative reziduale după "
                    "netarea documentelor de livrare/retur. Diferența rămasă "
                    "este păstrată separat pentru investigație."
                )
            result.cause_status = "PROBABILA"
            result.evidence_level = "B"

    inventory_adjustment_match = match_inventory_adjustments(
        wms_rows,
        wme_rows,
    )
    result.details["inventory_adjustment_matching"] = {
        "matches": inventory_adjustment_match.matches,
        "residual_wms_adjustments": (
            inventory_adjustment_match.residual_wms_adjustments
        ),
        "residual_wme_pv": inventory_adjustment_match.residual_wme_pv,
        "residual_wms_total": round(
            inventory_adjustment_match.residual_wms_total,
            decimals,
        ),
        "residual_wme_total": round(
            inventory_adjustment_match.residual_wme_total,
            decimals,
        ),
        "system_difference_effect": round(
            inventory_adjustment_match.system_difference_effect,
            decimals,
        ),
        "applied_to_explanation": False,
    }

    if inventory_adjustment_match.matches:
        matched_total = sum(
            float(item["quantity"])
            for item in inventory_adjustment_match.matches
        )
        result.findings.append(
            {
                "type": "INVENTORY_ADJUSTMENT_MATCH",
                "description": (
                    f"{len(inventory_adjustment_match.matches)} eveniment(e) "
                    f"de inventar WMS INV-PLS/INV-MIN au corespondent PV WME "
                    f"unic, total {matched_total:.3f} {result.unit}. "
                    "Aceste perechi se neutralizează între sisteme."
                ),
                "evidence": "SRC-WMS(INV-PLS/INV-MIN) + SRC-WME(PV)",
            }
        )

    if inventory_adjustment_match.residual_wms_adjustments:
        for item in inventory_adjustment_match.residual_wms_adjustments:
            result.unmatched_operations.append(
                {
                    "date": item["date"],
                    "system": "WMS",
                    "document": "-",
                    "operation_type": item["reason"],
                    "quantity": item["quantity"],
                    "reason": (
                        "Ajustare de inventar WMS fără PV WME unic "
                        "în fereastra validată."
                    ),
                    "status": item["status"],
                }
            )

    if inventory_adjustment_match.residual_wme_pv:
        for item in inventory_adjustment_match.residual_wme_pv:
            result.unmatched_operations.append(
                {
                    "date": item["date"],
                    "system": "WME",
                    "document": item["document"],
                    "operation_type": "PV",
                    "quantity": -float(item["quantity"]),
                    "reason": (
                        "PV WME fără ajustare WMS INV-PLS/INV-MIN unică "
                        "în fereastra validată."
                    ),
                    "status": item["status"],
                }
            )

    inventory_effect = round(
        inventory_adjustment_match.system_difference_effect,
        decimals,
    )
    if (
        inventory_effect != 0
        and result.initial_difference != 0
        and (inventory_effect > 0)
        == (result.initial_difference > 0)
        and abs(
            result.explained_difference + inventory_effect
        )
        <= abs(result.initial_difference) + 10 ** (-decimals)
    ):
        result.explained_difference = round(
            result.explained_difference + inventory_effect,
            decimals,
        )
        result.unexplained_difference = round(
            result.initial_difference - result.explained_difference,
            decimals,
        )
        result.details["inventory_adjustment_matching"][
            "applied_to_explanation"
        ] = True
        result.cause_code = "CAUSE-INVENTORY-ADJUSTMENT"
        result.cause_description = (
            "Diferența este explicată de ajustări de inventar WMS "
            "INV-PLS/INV-MIN fără corespondent PV WME, după neutralizarea "
            "perechilor de inventar documentate în ambele sisteme."
        )
        result.cause_status = (
            "CONFIRMATA"
            if abs(result.unexplained_difference) <= 10 ** (-decimals)
            else "PROBABILA"
        )
        result.evidence_level = "A"
        result.verdict = "REVIEW"

    wme_residual_match = match_wme_residual_movements(
        wme_rows,
        excluded_warehouses={"DETERIORATE", "PROTAN", "MOSTRE"},
        excluded_indexes=(
            set(inventory_adjustment_match.matched_wme_indexes)
            | set(inventory_adjustment_match.reviewed_wme_pv_indexes)
            | receipt_match.matched_wme_indexes
        ),
    )
    result.details["wme_residual_movements"] = {
        "residual_movements": len(
            wme_residual_match.residual_movements
        ),
        "movements": wme_residual_match.residual_movements,
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
        "applied_to_explanation": False,
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
                result.details["generic_stock_corrections"][
                    "applied_to_explanation"
                ] = True
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
        "applied_to_explanation": False,
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
                result.details["special_status_matching"][
                    "applied_to_explanation"
                ] = True
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

    result.operation_timeline.extend(timeline_from_wms(wms_rows))
    result.operation_timeline.extend(timeline_from_wme(wme_rows))
    result.operation_timeline.extend(
        timeline_from_production(production_rows, product_code)
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
        if offsetting_zone_differences:
            result.verdict = "REVIEW"
            result.evidence_level = "A"
            result.cause_code = "CAUSE-OFFSETTING-ZONE-DIFFERENCES"
            result.cause_description = (
                "Diferența totală pe produs este zero doar prin compensarea "
                "unor diferențe materiale între gestiunile/zonele raportului. "
                "Este necesară validarea mapării operaționale înainte de "
                "închiderea cazului."
            )
            result.cause_status = "CONFIRMATA"
            result.explained_difference = 0.0
            result.unexplained_difference = 0.0
        else:
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

    auto_explain = auto_explanation_from_investigation(
        result,
        decimals=decimals,
    )
    result.details["auto_explain"] = auto_explanation_to_dict(auto_explain)

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
