"""Pilot operator interface (read-only). Launch with: streamlit run operator_app.py."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from traceai_reconciliation.investigation import InvestigationSources, run_self_service_case
from traceai_reconciliation.loaders import read_table


REQUIRED_INPUTS = {
    "stock_report": "Raport stoc WMS/WME",
    "opening_stock_wms": "Stoc inițial WMS",
    "wms_movements": "Trasabilitate / mișcări WMS",
    "wme_ledger": "Fișă magazie WME",
    "production": "Rapoarte producție",
    "nomenclature": "Nomenclator mapare WMS/WME",
}
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
    frame = frame[frame["CodArticol"].notna() & frame["CodArticol"].ne("")]
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


def _write_uploaded_file(uploaded, destination: Path) -> Path:
    """Save into a private per-session local folder; never write into Git."""
    destination.mkdir(parents=True, exist_ok=True)
    filename = Path(uploaded.name).name
    ext = Path(filename).suffix.lower()
    if ext not in {".csv", ".xls", ".xlsx"}:
        raise ValueError("Format neacceptat. Sunt permise CSV/XLS/XLSX.")
    path = destination / filename
    path.write_bytes(uploaded.getvalue())
    return path


def main() -> None:
    st.set_page_config(page_title="TraceAI Control — Pilot", layout="wide")
    st.title("TraceAI Control — verificare scriptică WMS ↔ WME")
    st.caption("Pilot read-only. Operatorul decide corecțiile. REVIEW nu înseamnă eroare confirmată.")
    if "pilot_workspace" not in st.session_state:
        st.session_state.pilot_workspace = tempfile.mkdtemp(prefix="traceai-operator-")
    workspace = Path(st.session_state.pilot_workspace)
    with st.expander("1. Importă sursele", expanded=True):
        uploads = {}
        for key, label in REQUIRED_INPUTS.items():
            uploads[key] = st.file_uploader(label, type=["csv", "xls", "xlsx"], key=f"upload_{key}")
        period = st.text_input("Perioada investigației (exact ca în exporturi)", value="01.01.2026 - 11.10.2026")
        st.caption("Toate cele șase surse sunt obligatorii pentru investigație. Nicio sursă absentă nu este tratată drept zero.")
    stock_upload = uploads["stock_report"]
    if stock_upload is None:
        st.info("Importă raportul de stoc pentru a vedea toate articolele.")
        return
    try:
        paths = {
            key: _write_uploaded_file(value, workspace / "sources")
            for key, value in uploads.items() if value is not None
        }
        table = build_product_list(read_table(paths["stock_report"]))
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"Import blocat: {exc}")
        return

    st.subheader("2. Articole și diferențe")
    st.caption("Diferenta = WMS − WME. Articolele cu diferență zero pot fi investigate.")
    show = st.radio("Afișare", ["Toate", "Cu diferență", "Fără diferență"], horizontal=True)
    search = st.text_input("Caută după cod sau denumire", value="")
    selected = table
    if show == "Cu diferență":
        selected = selected[selected["Diferenta_WMS_minus_WME"].abs() > 0.001]
    elif show == "Fără diferență":
        selected = selected[selected["Diferenta_WMS_minus_WME"].abs() <= 0.001]
    if search.strip():
        mask = selected["CodArticol"].str.contains(search.strip(), case=False, regex=False, na=False)
        mask |= selected["DenumireArticol"].astype("string").str.contains(
            search.strip(), case=False, regex=False, na=False
        )
        selected = selected[mask]
    st.dataframe(selected, use_container_width=True, hide_index=True)
    codes = selected["CodArticol"].tolist()
    if not codes:
        st.info("Niciun articol în filtrul selectat.")
        return
    code = st.selectbox("3. Alege articolul pentru investigație", codes)
    if not st.button("4. Reconciliază articolul", type="primary"):
        return
    missing = [REQUIRED_INPUTS[key] for key in REQUIRED_INPUTS if key not in paths]
    if missing:
        st.error("Investigația nu poate porni. Lipsesc: " + ", ".join(missing))
        return
    if not period.strip():
        st.error("Perioada trebuie completată.")
        return
    sources = InvestigationSources(
        stock_report=paths["stock_report"],
        opening_stock_wms=paths["opening_stock_wms"],
        wms_movements=paths["wms_movements"],
        wme_ledger=paths["wme_ledger"],
        production=paths["production"],
        nomenclature=paths["nomenclature"],
        cache_dir=workspace / "cache",
        use_source_index=True,
        opening_absent_means_zero=False,
    )
    with st.spinner("TraceAI verifică operațiunile din sursele originale..."):
        try:
            result = run_self_service_case(
                product_code=code,
                period=period.strip(),
                sources=sources,
                output_dir=workspace / "cases",
                execution_id=f"operator:{code}",
            )
        except Exception as exc:
            st.error(f"Analiza este blocată și nu se declară MATCH: {type(exc).__name__}: {exc}")
            return
    st.success("Investigația a fost executată. Verifică verdictul și dovezile înainte de corecții.")
    case_dir = workspace / "cases" / f"CASE-SELF-{code}"
    docx = case_dir / "case.docx"
    json_file = case_dir / "case.json"
    for file, label, mime in [
        (docx, "Descarcă raport DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (json_file, "Descarcă dovezi JSON", "application/json"),
    ]:
        if file.is_file():
            st.download_button(label, data=file.read_bytes(), file_name=file.name, mime=mime)
    st.info("Documentele pot conține REVIEW. Corecțiile de stoc sunt decise și efectuate exclusiv de operator.")


if __name__ == "__main__":
    main()
