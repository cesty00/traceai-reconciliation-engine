"""Pilot operator interface (read-only). Launch with: streamlit run operator_app.py."""
from __future__ import annotations

from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from traceai_reconciliation.investigation import InvestigationSources, run_self_service_case
from traceai_reconciliation.loaders import read_table
from traceai_reconciliation.local_source_detection import discover_source_files


REQUIRED_INPUTS = {
    "stock_report": "Raport stoc WMS/WME",
    "opening_stock_wms": "Stoc inițial WMS",
    "wms_movements": "Trasabilitate / mișcări WMS",
    "wme_ledger": "Fișă magazie WME",
    "production": "Rapoarte producție",
    "nomenclature": "Nomenclator mapare WMS/WME",
}
from traceai_reconciliation.operator_stock_view import build_product_list, split_unidentified_articles
from traceai_reconciliation.operator_pilot_matrix import build_pilot_sample


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
    with st.expander("1. Selectează folderul local cu exporturi", expanded=True):
        folder_text = st.text_input(
            "Calea folderului de pe calculatorul pe care rulează Streamlit",
            placeholder=r"C:\\TraceAI\\Import\\2026-10-22",
        )
        period = st.text_input("Perioada investigației", value="01.01.2026 - 11.10.2026")
        st.caption("Streamlit rulează local; folderul trebuie să existe pe același calculator.")
        if not folder_text.strip():
            st.info("Introdu calea folderului local care conține exporturile.")
            return
        try:
            root = Path(folder_text.strip().strip('"')).expanduser().resolve()
            detected, problems = discover_source_files(root)
            available = sorted(
                p for p in root.iterdir()
                if p.is_file() and p.suffix.lower() in {".csv", ".xls", ".xlsx"}
                and not p.name.startswith("~$")
            )
        except (ValueError, OSError) as exc:
            st.error(f"Folder indisponibil: {exc}")
            return
        paths = {}
        for key, label in REQUIRED_INPUTS.items():
            default = detected.get(key)
            names = ["— Selectează fișierul —"] + [p.name for p in available]
            position = names.index(default.name) if default and default.name in names else 0
            selected_name = st.selectbox(label, names, index=position, key=f"local_{key}")
            if selected_name != names[0]:
                paths[key] = root / selected_name
            elif key in problems and problems[key]:
                st.warning(f"{label}: mai multe fișiere candidate. Alege manual.")
        duplicates = [p for p in paths.values() if list(paths.values()).count(p) > 1]
        if duplicates:
            st.error("Același fișier este asociat mai multor surse. Corectează selecția.")
            return
        if "stock_report" not in paths:
            st.info("Asociază raportul de stoc pentru a vedea lista articolelor.")
            return
    try:
        report = read_table(paths["stock_report"])
        identified, unidentified = split_unidentified_articles(report)
        if identified.empty:
            raise ValueError("Nu există articole cu cod identificabil în raport.")
        table = build_product_list(identified)
    except (ValueError, OSError, KeyError) as exc:
        st.error(f"Raport de stoc invalid: {exc}")
        return

    if not unidentified.empty:
        st.warning(f"{len(unidentified)} rânduri fără cod articol au fost izolate pentru verificarea mapării WMS/WME. Nu pot fi reconciliate automat.")
        with st.expander("Articole neidentificate — necesită mapare"):
            st.dataframe(unidentified, use_container_width=True, hide_index=True)
    with st.expander("Pilot QA — eșantion de testare (cu și fără diferență)"):
        st.caption(
            "Eșantion determinist: câte 3 produse WMS > WME, WMS < WME și fără diferență. "
            "Nu este un verdict al motorului; nu presupune că articolele cu sold zero sunt reconciliate."
        )
        matrix = build_pilot_sample(table, per_category=3)
        st.dataframe(matrix, use_container_width=True, hide_index=True)
        st.download_button(
            "Descarcă planul de testare CSV",
            data=matrix.to_csv(index=False).encode("utf-8-sig"),
            file_name="traceai_plan_testare_articole.csv",
            mime="text/csv",
        )
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
