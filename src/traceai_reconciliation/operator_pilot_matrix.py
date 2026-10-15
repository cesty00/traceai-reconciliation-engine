"""Deterministic operator QA sampling across stock difference categories.

This is a test-selection aid, NOT a reconciliation verdict.
"""
from __future__ import annotations
import pandas as pd

TOLERANCE = 0.001


def build_pilot_sample(products: pd.DataFrame, per_category: int = 3) -> pd.DataFrame:
    """Select reproducible examples from positive, negative and zero stock gaps."""
    required = {"CodArticol", "Diferenta_WMS_minus_WME"}
    missing = required.difference(products.columns)
    if missing:
        raise ValueError(f"Missing sample columns: {sorted(missing)}")
    if not isinstance(per_category, int) or per_category < 1:
        raise ValueError("per_category must be a positive integer")
    if products["CodArticol"].isna().any() or products["CodArticol"].astype("string").str.strip().eq("").any():
        raise ValueError("Pilot sampling requires identified article codes")
    difference = pd.to_numeric(products["Diferenta_WMS_minus_WME"], errors="coerce")
    if difference.isna().any():
        raise ValueError("Pilot sampling requires numeric stock differences")
    frame = products.copy()
    frame["Tip_test"] = "ZERO"
    frame.loc[difference > TOLERANCE, "Tip_test"] = "WMS_MAI_MARE"
    frame.loc[difference < -TOLERANCE, "Tip_test"] = "WME_MAI_MARE"
    frame["Marime_absoluta"] = difference.abs()
    frames = []
    for kind in ("WMS_MAI_MARE", "WME_MAI_MARE", "ZERO"):
        candidates = frame.loc[frame["Tip_test"] == kind].sort_values(
            ["Marime_absoluta", "CodArticol"], ascending=[False, True],
            kind="stable",
        ).head(per_category)
        frames.append(candidates)
    if not any(len(f) for f in frames):
        return frame.head(0).drop(columns=["Marime_absoluta"])
    result = pd.concat(frames, ignore_index=True)
    result["Stadiu_QA"] = "NETESTAT"
    result["Observatii_operator"] = ""
    return result.drop(columns=["Marime_absoluta"])
