"""Read-only stock overview calculations."""
from __future__ import annotations
import pandas as pd

REQUIRED_COLUMNS = {
    "CodArticol", "DenumireArticol", "QuantityWMS", "QuantityERP",
}


def build_product_list(report: pd.DataFrame) -> pd.DataFrame:
    """Aggregate every product, including zero-difference products.

    Calculate the difference from WMS and ERP balances; the reported
    QuantityDifference is a separate cross-check, never a substitute.
    """
    missing = REQUIRED_COLUMNS.difference(report.columns)
    if missing:
        raise ValueError("Raportul de stoc nu conține coloanele: " + ", ".join(sorted(missing)))
    frame = report.copy()
    frame["CodArticol"] = frame["CodArticol"].astype("string").str.strip()
    if frame["CodArticol"].isna().any() or frame["CodArticol"].eq("").any():
        raise ValueError("CodArticol lipsă: importul trebuie verificat.")
    for field in ("QuantityWMS", "QuantityERP"):
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
        if frame[field].isna().any():
            raise ValueError(f"Valori lipsă sau nenumerice în {field}; importul este blocat.")
    grouped = frame.groupby("CodArticol", sort=True, as_index=False).agg(
        DenumireArticol=("DenumireArticol", "first"),
        WMS=("QuantityWMS", "sum"),
        WME=("QuantityERP", "sum"),
    )
    grouped["Diferenta_WMS_minus_WME"] = grouped["WMS"] - grouped["WME"]
    if "QuantityDifference" in frame.columns:
        reported = pd.to_numeric(frame["QuantityDifference"], errors="coerce")
        if reported.isna().any():
            raise ValueError("QuantityDifference conține valori nenumerice.")
        grouped = grouped.merge(
            frame.assign(_reported=reported).groupby("CodArticol", as_index=False)["_reported"].sum(),
            on="CodArticol",
            how="left",
        )
        grouped["Concordanta_cu_raportul"] = (
            (grouped["Diferenta_WMS_minus_WME"] - grouped["_reported"]).abs() <= 0.001
        )
        grouped = grouped.drop(columns="_reported")
    return grouped




def split_unidentified_articles(report: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate missing-code source rows for explicit operator review.

    Never invent a mapping, erase original quantities, or silently remove
    unidentifiable records. The caller must display the quarantined rows.
    """
    missing = REQUIRED_COLUMNS.difference(report.columns)
    if missing:
        raise ValueError("Raportul de stoc nu conține coloanele: " + ", ".join(sorted(missing)))
    codes = report["CodArticol"].astype("string").str.strip()
    unidentified = codes.isna() | codes.eq("")
    return report.loc[~unidentified].copy(), report.loc[unidentified].copy()


def build_warehouse_stock_view(report: pd.DataFrame) -> pd.DataFrame:
    """Preserve WMS/WME stock totals separately for each *reported* gestiune.

    This view does not assert that WMS locations are proven mapped to
    WME gestiuni. It reproduces the scope labels in the original stock
    report for operator review. Never merge different gestiuni.
    """
    required = REQUIRED_COLUMNS | {"Gestiune"}
    missing = required.difference(report.columns)
    if missing:
        raise ValueError("Raportul nu conține coloanele necesare afișării gestiunilor: " + ", ".join(sorted(missing)))
    frame = report.copy()
    frame["CodArticol"] = frame["CodArticol"].astype("string").str.strip()
    frame["Gestiune"] = frame["Gestiune"].astype("string").str.strip()
    if (frame["CodArticol"].isna() | frame["CodArticol"].eq("")).any():
        raise ValueError("CodArticol lipsă: separă articolele neidentificate înainte de afișare.")
    if (frame["Gestiune"].isna() | frame["Gestiune"].eq("")).any():
        raise ValueError("Gestiune lipsă: nu se atribuie automat o gestiune.")
    for field in ("QuantityWMS", "QuantityERP"):
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
        if frame[field].isna().any():
            raise ValueError(f"Valori invalide în {field}.")
    grouped = frame.groupby(["CodArticol", "Gestiune"], as_index=False, sort=True).agg(
        DenumireArticol=("DenumireArticol", "first"),
        WMS=("QuantityWMS", "sum"),
        WME=("QuantityERP", "sum"),
    )
    grouped["Diferenta_WMS_minus_WME"] = grouped["WMS"] - grouped["WME"]
    return grouped


def build_depozitare_consolidated_view(warehouse_view: pd.DataFrame) -> pd.DataFrame:
    """Operator-approved physical scope: Receptie is staging within Depozitare.

    Preserve original gestiune rows in warehouse_view. This is a read-only
    consolidation, not a documentary MATCH or authorization for adjustment.
    """
    required = {"CodArticol", "Gestiune", "WMS", "WME"}
    missing = required.difference(warehouse_view.columns)
    if missing:
        raise ValueError("Coloane lipsă pentru consolidare: " + ", ".join(sorted(missing)))
    frame = warehouse_view.copy()
    names = frame["Gestiune"].astype("string").str.strip().str.upper()
    eligible = names.isin(["DEPOZITARE", "RECEPTIE", "RECEPȚIE"])
    scoped = frame.loc[eligible].copy()
    if scoped.empty:
        return pd.DataFrame(columns=["CodArticol", "Perimetru", "WMS", "WME", "Diferenta_WMS_minus_WME", "Zone_incluse"])
    for field in ("WMS", "WME"):
        scoped[field] = pd.to_numeric(scoped[field], errors="coerce")
        if scoped[field].isna().any():
            raise ValueError(f"Cantitate invalidă la consolidare: {field}")
    grouped = scoped.groupby("CodArticol", as_index=False).agg(
        WMS=("WMS", "sum"),
        WME=("WME", "sum"),
        Zone_incluse=("Gestiune", lambda s: ", ".join(sorted(set(s)))),
    )
    grouped.insert(1, "Perimetru", "Depozitare (include Recepție nerelocată)")
    grouped["Diferenta_WMS_minus_WME"] = grouped["WMS"] - grouped["WME"]
    return grouped
