from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class TransferMoseMatchResult:
    matches: list[dict[str, Any]]
    cancelled_orders: list[dict[str, Any]]
    residual_wms_transfers: list[dict[str, Any]]
    wme_only_nt: list[dict[str, Any]]
    matched_wms_total: float
    residual_wms_total: float


def normalize_transfer_mose_order(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    if not text.startswith("TRANSFER_MOSE"):
        return ""
    return re.sub(r"_DEL_.*$", "", text)


def _normalize_document(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except (TypeError, ValueError):
        match = re.search(r"(\d+)", text)
        return str(int(match.group(1))) if match else ""


def _date(value: object) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).normalize()


def match_transfer_mose(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    tolerance: float = 0.001,
    lag_days: int = 2,
) -> TransferMoseMatchResult:
    """
    Match WMS TRANSFER_MOSE operations with WME NT between DP and MOSE.

    The matcher is deliberately conservative:
    - technical _DEL_<UUID> rows are netted into the base WMS order;
    - zero-net WMS orders are treated as cancelled after netting;
    - exact WME document linkage has priority;
    - fallback matching requires a unique product-level candidate with the
      same direction and quantity, on the same day or within lag_days;
    - ambiguous or missing-integration cases remain REVIEW.

    The matcher supplies operational evidence only and does not by itself
    change the product-level WMS-WME stock difference.
    """
    if wms_rows.empty:
        return TransferMoseMatchResult([], [], [], [], 0.0, 0.0)

    minimum_wms = {
        "Data",
        "Tip operatiune",
        "Cantitate",
    }
    missing_minimum = minimum_wms - set(wms_rows.columns)
    if missing_minimum:
        raise ValueError(
            "TRANSFER_MOSE matching: coloane WMS de bază lipsă "
            f"{sorted(missing_minimum)}"
        )

    # If the source does not expose the order column, the specific
    # TRANSFER_MOSE family cannot be identified. Treat the matcher as a no-op
    # instead of breaking unrelated product investigations.
    if "Numar comanda" not in wms_rows.columns:
        return TransferMoseMatchResult([], [], [], [], 0.0, 0.0)

    work = wms_rows.copy()
    work["_order"] = work["Numar comanda"].map(normalize_transfer_mose_order)
    work = work[work["_order"].ne("")].copy()
    if work.empty:
        return TransferMoseMatchResult([], [], [], [], 0.0, 0.0)

    work["_op"] = work["Tip operatiune"].astype(str).str.strip()
    work = work[work["_op"].isin(["Livrare", "Receptie"])].copy()
    if work.empty:
        return TransferMoseMatchResult([], [], [], [], 0.0, 0.0)

    work["_qty"] = pd.to_numeric(
        work["Cantitate"], errors="coerce"
    ).fillna(0.0)
    work["_date"] = pd.to_datetime(
        work["Data"], errors="coerce", dayfirst=True
    ).dt.normalize()
    work["_direction"] = work["_op"].map(
        {"Livrare": "DP->MOSE", "Receptie": "MOSE->DP"}
    )

    if "Document intrare" in work.columns:
        work["_document_in"] = work["Document intrare"].map(
            _normalize_document
        )
    else:
        work["_document_in"] = ""

    if "Document comanda" in work.columns:
        work["_document_order"] = (
            work["Document comanda"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        work["_document_order"] = ""

    wms_orders: list[dict[str, Any]] = []
    cancelled_orders: list[dict[str, Any]] = []

    for (order, direction), group in work.groupby(
        ["_order", "_direction"],
        dropna=False,
    ):
        net_qty = float(group["_qty"].sum())
        first_date = group["_date"].min()
        last_date = group["_date"].max()
        document_in = sorted(
            {
                value
                for value in group["_document_in"].tolist()
                if value
            }
        )
        document_order = sorted(
            {
                value
                for value in group["_document_order"].tolist()
                if value
            }
        )

        item = {
            "order": str(order),
            "direction": str(direction),
            "net_quantity": net_qty,
            "amount": abs(net_qty),
            "first_date": first_date,
            "last_date": last_date,
            "document_in": document_in,
            "document_order": document_order,
        }

        if abs(net_qty) <= tolerance:
            item["status"] = "MATCH_DUPA_NETARE"
            cancelled_orders.append(item)
            continue

        expected_sign = -1.0 if direction == "DP->MOSE" else 1.0
        if net_qty * expected_sign <= 0:
            item["status"] = "SIGN_CONFLICT_REVIEW"
            wms_orders.append(item)
            continue

        item["status"] = "PENDING"
        wms_orders.append(item)

    required_wme = {
        "Date",
        "OperationType",
        "Document",
        "SignedQuantity",
        "Warehouse",
        "Partner",
    }
    if not required_wme.issubset(wme_rows.columns):
        residual = [
            {
                **item,
                "status": "WME_COLUMNS_MISSING_REVIEW",
            }
            for item in wms_orders
        ]
        return TransferMoseMatchResult(
            matches=[],
            cancelled_orders=cancelled_orders,
            residual_wms_transfers=residual,
            wme_only_nt=[],
            matched_wms_total=0.0,
            residual_wms_total=float(
                sum(item["net_quantity"] for item in residual)
            ),
        )

    wme = wme_rows.copy()
    wme["_op"] = (
        wme["OperationType"].astype(str).str.strip().str.upper()
    )
    wme["_warehouse"] = (
        wme["Warehouse"].astype(str).str.strip().str.upper()
    )
    wme["_partner"] = (
        wme["Partner"].astype(str).str.strip().str.upper()
    )
    wme["_qty"] = pd.to_numeric(
        wme["SignedQuantity"], errors="coerce"
    ).fillna(0.0)
    wme["_date"] = pd.to_datetime(
        wme["Date"], errors="coerce", dayfirst=True
    ).dt.normalize()
    wme["_document"] = wme["Document"].map(_normalize_document)

    # Use only the DEPOZIT PRINCIPAL leg to avoid counting both sides of NT.
    wme = wme[
        wme["_op"].eq("NT")
        & wme["_warehouse"].eq("DEPOZIT PRINCIPAL")
        & wme["_partner"].eq("MOSE")
        & wme["_document"].ne("")
    ].copy()

    wme["_direction"] = wme["_qty"].map(
        lambda value: "DP->MOSE" if value < 0 else "MOSE->DP"
    )

    wme_docs: list[dict[str, Any]] = []
    for (document, direction), group in wme.groupby(
        ["_document", "_direction"],
        dropna=False,
    ):
        signed_qty = float(group["_qty"].sum())
        wme_docs.append(
            {
                "document": str(document),
                "direction": str(direction),
                "signed_quantity": signed_qty,
                "amount": abs(signed_qty),
                "date": group["_date"].min(),
            }
        )

    used_wme: set[int] = set()
    used_wms: set[int] = set()
    matches: list[dict[str, Any]] = []

    def add_match(
        wms_index: int,
        wme_index: int,
        method: str,
    ) -> None:
        wms_item = wms_orders[wms_index]
        wme_item = wme_docs[wme_index]
        lag = None
        if (
            wms_item["first_date"] is not pd.NaT
            and wme_item["date"] is not pd.NaT
        ):
            lag = int(
                (wme_item["date"] - wms_item["first_date"]).days
            )

        matches.append(
            {
                "order": wms_item["order"],
                "direction": wms_item["direction"],
                "wms_quantity": wms_item["net_quantity"],
                "wms_amount": wms_item["amount"],
                "wme_document": wme_item["document"],
                "wme_signed_quantity": wme_item["signed_quantity"],
                "wme_amount": wme_item["amount"],
                "wms_first_date": wms_item["first_date"],
                "wme_date": wme_item["date"],
                "lag_days": lag,
                "method": method,
                "status": "MATCH",
            }
        )
        used_wms.add(wms_index)
        used_wme.add(wme_index)

    # 1) Strongest link: WMS Document intrare == WME NT document.
    for wi, item in enumerate(wms_orders):
        if wi in used_wms or not item["document_in"]:
            continue

        candidates = [
            (ni, nt)
            for ni, nt in enumerate(wme_docs)
            if ni not in used_wme
            and nt["direction"] == item["direction"]
            and nt["document"] in item["document_in"]
        ]
        if len(candidates) != 1:
            continue

        ni, nt = candidates[0]
        if abs(nt["amount"] - item["amount"]) <= tolerance:
            add_match(wi, ni, "DIRECT_DOCUMENT")
        else:
            item["direct_document_candidate"] = {
                "document": nt["document"],
                "wme_amount": nt["amount"],
                "difference": item["amount"] - nt["amount"],
            }

    # 2) Same day + same quantity, only when the relation is one-to-one.
    key_to_wms: dict[tuple[object, ...], list[int]] = {}
    key_to_wme: dict[tuple[object, ...], list[int]] = {}

    for wi, item in enumerate(wms_orders):
        if wi in used_wms:
            continue
        key = (
            item["direction"],
            round(float(item["amount"]), 3),
            item["first_date"],
        )
        key_to_wms.setdefault(key, []).append(wi)

    for ni, item in enumerate(wme_docs):
        if ni in used_wme:
            continue
        key = (
            item["direction"],
            round(float(item["amount"]), 3),
            item["date"],
        )
        key_to_wme.setdefault(key, []).append(ni)

    for key, wms_indexes in key_to_wms.items():
        wme_indexes = key_to_wme.get(key, [])
        if len(wms_indexes) == 1 and len(wme_indexes) == 1:
            add_match(
                wms_indexes[0],
                wme_indexes[0],
                "SAME_DAY_QUANTITY",
            )

    # 3) Small timing lag, only for mutual unique candidates.
    candidate_map: dict[int, list[int]] = {}
    reverse_map: dict[int, list[int]] = {}

    for wi, item in enumerate(wms_orders):
        if wi in used_wms:
            continue

        candidates: list[int] = []
        for ni, nt in enumerate(wme_docs):
            if ni in used_wme:
                continue
            if nt["direction"] != item["direction"]:
                continue
            if abs(nt["amount"] - item["amount"]) > tolerance:
                continue
            if item["first_date"] is pd.NaT or nt["date"] is pd.NaT:
                continue
            lag = int((nt["date"] - item["first_date"]).days)
            if abs(lag) <= lag_days:
                candidates.append(ni)

        candidate_map[wi] = candidates
        for ni in candidates:
            reverse_map.setdefault(ni, []).append(wi)

    for wi, candidates in candidate_map.items():
        if wi in used_wms or len(candidates) != 1:
            continue
        ni = candidates[0]
        if len(reverse_map.get(ni, [])) != 1:
            continue
        add_match(wi, ni, "LAG_QUANTITY")

    residual_wms: list[dict[str, Any]] = []
    for wi, item in enumerate(wms_orders):
        if wi in used_wms:
            continue
        residual = dict(item)
        documents = " ".join(item["document_order"]).upper()
        if "NEPROCESAT" in documents:
            residual["status"] = "NEPROCESAT_REVIEW"
        elif not item["document_order"] and not item["document_in"]:
            residual["status"] = "NO_DOCUMENT_REVIEW"
        elif "direct_document_candidate" in item:
            residual["status"] = "QTY_DIFF_REVIEW"
        else:
            residual["status"] = "NO_NT_MATCH_REVIEW"
        residual_wms.append(residual)

    wme_only = [
        {
            **item,
            "status": "WME_ONLY_NT_REVIEW",
        }
        for ni, item in enumerate(wme_docs)
        if ni not in used_wme
    ]

    return TransferMoseMatchResult(
        matches=matches,
        cancelled_orders=cancelled_orders,
        residual_wms_transfers=residual_wms,
        wme_only_nt=wme_only,
        matched_wms_total=float(
            sum(item["wms_quantity"] for item in matches)
        ),
        residual_wms_total=float(
            sum(item["net_quantity"] for item in residual_wms)
        ),
    )


def match_transfer_mose_baskets(
    wms_rows: pd.DataFrame,
    wme_rows: pd.DataFrame,
    product_name: str,
    tolerance: float = 0.001,
    lag_days: int = 2,
) -> TransferMoseMatchResult:
    """
    Match TRANSFER_MOSE at whole-transfer basket level and return evidence
    scoped to one product.

    This resolves product-level ambiguity by requiring the complete set of
    products and net quantities in a WMS transfer order to equal the WME NT
    document basket. Technical _DEL_ rows are netted into the base order.

    Only exact basket signatures are matched. Quantity-different or missing
    integrations remain REVIEW.
    """
    if wms_rows.empty:
        return TransferMoseMatchResult([], [], [], [], 0.0, 0.0)

    required_wms = {
        "Data",
        "Tip operatiune",
        "Cantitate",
        "Numar comanda",
        "Denumire articol",
    }
    missing_wms = required_wms - set(wms_rows.columns)
    if missing_wms:
        raise ValueError(
            "TRANSFER_MOSE basket matching: coloane WMS lipsă "
            f"{sorted(missing_wms)}"
        )

    required_wme = {
        "Date",
        "OperationType",
        "Document",
        "SignedQuantity",
        "Warehouse",
        "Partner",
        "ProductName",
    }
    missing_wme = required_wme - set(wme_rows.columns)
    if missing_wme:
        raise ValueError(
            "TRANSFER_MOSE basket matching: coloane WME lipsă "
            f"{sorted(missing_wme)}"
        )

    target_product = str(product_name).strip()

    wms = wms_rows.copy()
    wms["_order"] = wms["Numar comanda"].map(
        normalize_transfer_mose_order
    )
    wms = wms[wms["_order"].ne("")].copy()
    if wms.empty:
        return TransferMoseMatchResult([], [], [], [], 0.0, 0.0)

    wms["_op"] = wms["Tip operatiune"].astype(str).str.strip()
    wms = wms[wms["_op"].isin(["Livrare", "Receptie"])].copy()
    wms["_qty"] = pd.to_numeric(
        wms["Cantitate"], errors="coerce"
    ).fillna(0.0)
    wms["_date"] = pd.to_datetime(
        wms["Data"], errors="coerce", dayfirst=True
    ).dt.normalize()
    wms["_direction"] = wms["_op"].map(
        {"Livrare": "DP->MOSE", "Receptie": "MOSE->DP"}
    )
    wms["_product"] = (
        wms["Denumire articol"].fillna("").astype(str).str.strip()
    )
    if "Document intrare" in wms.columns:
        wms["_document_in"] = wms["Document intrare"].map(
            _normalize_document
        )
    else:
        wms["_document_in"] = ""
    if "Document comanda" in wms.columns:
        wms["_document_order"] = (
            wms["Document comanda"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        wms["_document_order"] = ""

    # Net all rows by base order, direction and product across the period.
    net_product = (
        wms.groupby(
            ["_order", "_direction", "_product"],
            dropna=False,
        )["_qty"]
        .sum()
        .reset_index()
    )

    wms_orders: list[dict[str, Any]] = []
    cancelled_orders_all: list[dict[str, Any]] = []

    for (order, direction), group in net_product.groupby(
        ["_order", "_direction"],
        dropna=False,
    ):
        source_group = wms[
            wms["_order"].eq(order)
            & wms["_direction"].eq(direction)
        ]
        raw_products = {
            str(value).strip()
            for value in source_group["_product"].tolist()
            if str(value).strip()
        }

        product_quantities: dict[str, float] = {}
        signature_parts: list[tuple[str, float]] = []
        sign_conflict = False
        expected_sign = -1.0 if direction == "DP->MOSE" else 1.0

        for _, item in group.iterrows():
            name = str(item["_product"]).strip()
            quantity = round(float(item["_qty"]), 3)
            if not name or abs(quantity) <= tolerance:
                continue
            if quantity * expected_sign <= 0:
                sign_conflict = True
            product_quantities[name] = quantity
            signature_parts.append((name, round(abs(quantity), 3)))

        dates = sorted(
            {
                value
                for value in source_group["_date"].tolist()
                if not pd.isna(value)
            }
        )
        document_in = sorted(
            {
                value
                for value in source_group["_document_in"].tolist()
                if value
            }
        )
        document_order = sorted(
            {
                value
                for value in source_group["_document_order"].tolist()
                if value
            }
        )

        item = {
            "order": str(order),
            "direction": str(direction),
            "dates": dates,
            "first_date": dates[0] if dates else pd.NaT,
            "last_date": dates[-1] if dates else pd.NaT,
            "document_in": document_in,
            "document_order": document_order,
            "products": product_quantities,
            "raw_products": raw_products,
            "signature": tuple(sorted(signature_parts)),
            "amount": round(
                sum(quantity for _, quantity in signature_parts),
                3,
            ),
        }

        if not signature_parts:
            item["status"] = "MATCH_DUPA_NETARE"
            cancelled_orders_all.append(item)
            continue

        if sign_conflict:
            item["status"] = "SIGN_CONFLICT_REVIEW"
        else:
            item["status"] = "PENDING"
        wms_orders.append(item)

    wme = wme_rows.copy()
    wme["_op"] = (
        wme["OperationType"].astype(str).str.strip().str.upper()
    )
    wme["_warehouse"] = (
        wme["Warehouse"].astype(str).str.strip().str.upper()
    )
    wme["_partner"] = (
        wme["Partner"].astype(str).str.strip().str.upper()
    )
    wme["_qty"] = pd.to_numeric(
        wme["SignedQuantity"], errors="coerce"
    ).fillna(0.0)
    wme["_date"] = pd.to_datetime(
        wme["Date"], errors="coerce", dayfirst=True
    ).dt.normalize()
    wme["_document"] = wme["Document"].map(_normalize_document)
    wme["_product"] = (
        wme["ProductName"].fillna("").astype(str).str.strip()
    )

    # One accounting leg only, otherwise every NT is doubled.
    wme = wme[
        wme["_op"].eq("NT")
        & wme["_warehouse"].eq("DEPOZIT PRINCIPAL")
        & wme["_partner"].eq("MOSE")
        & wme["_document"].ne("")
    ].copy()
    wme["_direction"] = wme["_qty"].map(
        lambda value: "DP->MOSE" if value < 0 else "MOSE->DP"
    )

    wme_product = (
        wme.groupby(
            ["_document", "_date", "_direction", "_product"],
            dropna=False,
        )["_qty"]
        .sum()
        .reset_index()
    )

    wme_docs: list[dict[str, Any]] = []
    for (document, doc_date, direction), group in wme_product.groupby(
        ["_document", "_date", "_direction"],
        dropna=False,
    ):
        products: dict[str, float] = {}
        signature_parts: list[tuple[str, float]] = []
        for _, row in group.iterrows():
            name = str(row["_product"]).strip()
            quantity = round(float(row["_qty"]), 3)
            if not name or abs(quantity) <= tolerance:
                continue
            products[name] = quantity
            signature_parts.append((name, round(abs(quantity), 3)))

        if not signature_parts:
            continue

        wme_docs.append(
            {
                "document": str(document),
                "date": doc_date,
                "direction": str(direction),
                "products": products,
                "signature": tuple(sorted(signature_parts)),
                "amount": round(
                    sum(quantity for _, quantity in signature_parts),
                    3,
                ),
            }
        )

    used_wms: set[int] = set()
    used_wme: set[int] = set()
    matches_all: list[dict[str, Any]] = []

    def nearest_lag(
        order_dates: list[pd.Timestamp],
        wme_date: pd.Timestamp,
    ) -> int | None:
        if not order_dates or pd.isna(wme_date):
            return None
        lags = [
            int((wme_date - date).days)
            for date in order_dates
            if not pd.isna(date)
        ]
        if not lags:
            return None
        return min(lags, key=abs)

    def add_match(
        wi: int,
        ni: int,
        method: str,
    ) -> None:
        order = wms_orders[wi]
        nt = wme_docs[ni]
        matches_all.append(
            {
                "order": order["order"],
                "direction": order["direction"],
                "wms_quantity": order["products"].get(
                    target_product,
                    0.0,
                ),
                "wms_amount": abs(
                    order["products"].get(target_product, 0.0)
                ),
                "wme_document": nt["document"],
                "wme_signed_quantity": nt["products"].get(
                    target_product,
                    0.0,
                ),
                "wme_amount": abs(
                    nt["products"].get(target_product, 0.0)
                ),
                "wms_first_date": order["first_date"],
                "wme_date": nt["date"],
                "lag_days": nearest_lag(
                    order["dates"],
                    nt["date"],
                ),
                "method": method,
                "status": "MATCH",
                "basket_product_count": len(order["signature"]),
                "basket_amount": order["amount"],
            }
        )
        used_wms.add(wi)
        used_wme.add(ni)

    # Strongest evidence: exact document + exact basket.
    for wi, order in enumerate(wms_orders):
        if not order["document_in"]:
            continue
        candidates = [
            (ni, nt)
            for ni, nt in enumerate(wme_docs)
            if ni not in used_wme
            and nt["direction"] == order["direction"]
            and nt["document"] in order["document_in"]
        ]
        if len(candidates) != 1:
            continue
        ni, nt = candidates[0]
        if nt["signature"] == order["signature"]:
            add_match(wi, ni, "DIRECT_DOCUMENT_BASKET")
        else:
            order["direct_document_candidate"] = {
                "document": nt["document"],
                "wme_signature": nt["signature"],
            }

    # Exact whole-basket signature on the same day.
    remaining_wms_by_key: dict[
        tuple[object, ...],
        list[int],
    ] = {}
    remaining_wme_by_key: dict[
        tuple[object, ...],
        list[int],
    ] = {}

    for wi, order in enumerate(wms_orders):
        if wi in used_wms:
            continue
        for order_date in order["dates"]:
            key = (
                order["direction"],
                order["signature"],
                order_date,
            )
            remaining_wms_by_key.setdefault(key, []).append(wi)

    for ni, nt in enumerate(wme_docs):
        if ni in used_wme:
            continue
        key = (
            nt["direction"],
            nt["signature"],
            nt["date"],
        )
        remaining_wme_by_key.setdefault(key, []).append(ni)

    for key, wms_indexes in remaining_wms_by_key.items():
        wme_indexes = remaining_wme_by_key.get(key, [])
        unique_wms = sorted(set(wms_indexes))
        unique_wme = sorted(set(wme_indexes))
        if len(unique_wms) == 1 and len(unique_wme) == 1:
            wi = unique_wms[0]
            ni = unique_wme[0]
            if wi not in used_wms and ni not in used_wme:
                add_match(wi, ni, "SAME_DAY_BASKET")

    # Exact whole-basket signature with a small lag, mutual unique only.
    candidate_map: dict[int, list[int]] = {}
    reverse_map: dict[int, list[int]] = {}

    for wi, order in enumerate(wms_orders):
        if wi in used_wms:
            continue
        candidates: list[int] = []
        for ni, nt in enumerate(wme_docs):
            if ni in used_wme:
                continue
            if nt["direction"] != order["direction"]:
                continue
            if nt["signature"] != order["signature"]:
                continue
            lag = nearest_lag(order["dates"], nt["date"])
            if lag is not None and abs(lag) <= lag_days:
                candidates.append(ni)
        candidate_map[wi] = candidates
        for ni in candidates:
            reverse_map.setdefault(ni, []).append(wi)

    for wi, candidates in candidate_map.items():
        if wi in used_wms or len(candidates) != 1:
            continue
        ni = candidates[0]
        if len(reverse_map.get(ni, [])) != 1:
            continue
        add_match(wi, ni, "LAG_BASKET")

    # Scope the result to the requested product.
    scoped_matches = [
        item
        for item in matches_all
        if abs(float(item["wms_quantity"])) > tolerance
        or abs(float(item["wme_signed_quantity"])) > tolerance
    ]

    cancelled_orders = [
        {
            **item,
            "net_quantity": 0.0,
        }
        for item in cancelled_orders_all
        if target_product in item["raw_products"]
    ]

    residual_wms: list[dict[str, Any]] = []
    for wi, order in enumerate(wms_orders):
        if wi in used_wms or target_product not in order["products"]:
            continue

        quantity = float(order["products"][target_product])
        residual = {
            **order,
            "net_quantity": quantity,
            "amount": abs(quantity),
        }
        documents = " ".join(order["document_order"]).upper()
        if "NEPROCESAT" in documents:
            residual["status"] = "NEPROCESAT_REVIEW"
        elif not order["document_order"] and not order["document_in"]:
            residual["status"] = "NO_DOCUMENT_REVIEW"
        elif "direct_document_candidate" in order:
            residual["status"] = "QTY_DIFF_REVIEW"
        else:
            residual["status"] = "NO_NT_MATCH_REVIEW"
        residual_wms.append(residual)

    wme_only: list[dict[str, Any]] = []
    for ni, nt in enumerate(wme_docs):
        if ni in used_wme or target_product not in nt["products"]:
            continue
        quantity = float(nt["products"][target_product])
        wme_only.append(
            {
                "document": nt["document"],
                "date": nt["date"],
                "direction": nt["direction"],
                "signed_quantity": quantity,
                "amount": abs(quantity),
                "status": "WME_ONLY_NT_REVIEW",
            }
        )

    return TransferMoseMatchResult(
        matches=scoped_matches,
        cancelled_orders=cancelled_orders,
        residual_wms_transfers=residual_wms,
        wme_only_nt=wme_only,
        matched_wms_total=float(
            sum(item["wms_quantity"] for item in scoped_matches)
        ),
        residual_wms_total=float(
            sum(item["net_quantity"] for item in residual_wms)
        ),
    )
