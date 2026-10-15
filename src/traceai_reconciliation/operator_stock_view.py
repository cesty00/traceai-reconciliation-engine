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
