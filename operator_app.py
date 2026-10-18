"""Pilot operator interface (read-only). Launch with: streamlit run operator_app.py."""
from __future__ import annotations

from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from traceai_reconciliation.investigation import InvestigationSources, run_self_service_case
from traceai_reconciliation.loaders import read_table
from traceai_reconciliation.local_source_detection import discover_source_files
from traceai_reconciliation.investigation.operator_report_registry import record_generated_report, list_generated_reports, report_filename
from traceai_reconciliation.investigation.operator_status import STATUSES, latest_operator_statuses, set_operator_status


REQUIRED_INPUTS = {
    "stock_report": "Raport stoc WMS/WME",
    "opening_stock_wms": "Stoc inițial WMS",
    "wms_movements": "Trasabilitate / mișcări WMS",
    "wme_ledger": "Fișă magazie WME",
    "production": "Rapoarte producție",
    "nomenclature": "Nomenclator mapare WMS/WME",
}
from traceai_reconciliation.operator_stock_view import build_product_list, split_unidentified_articles, build_warehouse_stock_view, build_depozitare_consolidated_view
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
    with st.expander("Registrul verificărilor — rapoarte arhivate", expanded=False):
        try:
            history = list_generated_reports()
            if history:
                registry_table = pd.DataFrame([{
                    "Data": item["recorded_at"],
                    "Articol": item["product_code"],
                    "Denumire": item["product_name"],
                    "Perioada": item["period"],
                    "Diferența": item["difference"],
                    "UM": item["unit"],
                    "Verdict motor": item["engine_verdict"],
                    "ID rulare": item["run_id"],
                } for item in history])
                registry_search = st.text_input("Caută în registru după cod sau denumire", key="registry_search")
                if registry_search.strip():
                    mask = registry_table["Articol"].astype(str).str.contains(registry_search.strip(), case=False, regex=False)
                    mask |= registry_table["Denumire"].astype(str).str.contains(registry_search.strip(), case=False, regex=False)
                    filtered = registry_table[mask]
                else:
                    filtered = registry_table
                st.dataframe(filtered, use_container_width=True, hide_index=True)
                st.download_button(
                    "Exportă registrul CSV",
                    data=registry_table.to_csv(index=False).encode("utf-8-sig"),
                    file_name="traceai_registru_verificari.csv",
                    mime="text/csv",
                )
                selectable_runs = filtered["ID rulare"].tolist()
                if not selectable_runs:
                    st.info("Nu există verificări pentru filtrul selectat.")
                    selected_run = None
                else:
                    selected_run = st.selectbox(
                    "Selectează verificarea arhivată",
                    selectable_runs,
                )
                chosen = next((item for item in history if item["run_id"] == selected_run), None)
                for filename, label, mime in [
                    ("docx_path", "Descarcă DOCX arhivat", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                    ("json_path", "Descarcă JSON arhivat", "application/json"),
                ]:
                    archived = Path(chosen[filename]) if chosen is not None else None
                    if archived is not None and archived.is_file():
                        st.download_button(label, data=archived.read_bytes(),
                                           file_name=report_filename(chosen["product_code"], chosen["run_id"], archived.suffix.lstrip(".")),
                                           mime=mime, key=f"archive_{selected_run}_{filename}")
                    elif archived is not None:
                        st.error(f"Fișier arhivat lipsă: {archived.name}")
            else:
                st.info("Nu există verificări arhivate încă.")
        except (OSError, ValueError) as exc:
            st.error(f"Registrul verificărilor nu poate fi citit: {exc}")
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
        warehouse_table = build_warehouse_stock_view(identified)
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
    st.subheader("2. Raport unic de stoc — produs + gestiune")
    st.caption(
        "Un rând = un articol într-o gestiune. Diferența = WMS − WME. "
        "Soldurile egale nu înseamnă operațiuni reconciliate. "
        "Selectarea unei gestiuni NU limitează investigația motorului la acea gestiune."
    )
    product_count = len(table)
    difference_count = int((warehouse_table["Diferenta_WMS_minus_WME"].abs() > 0.001).sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Articole", product_count)
    m2.metric("Poziții produs–gestiune", len(warehouse_table))
    m3.metric("Poziții cu diferență", difference_count)

    show = st.radio("Afișare", ["Toate", "Cu diferență", "Fără diferență"], horizontal=True)
    search = st.text_input("Caută după cod, denumire sau gestiune", value="")
    gestiuni = sorted(warehouse_table["Gestiune"].dropna().astype(str).unique().tolist())
    warehouse_filter = st.selectbox("Filtru gestiune", ["Toate gestiunile", *gestiuni])

    selected = warehouse_table.copy()
    if show == "Cu diferență":
        selected = selected[selected["Diferenta_WMS_minus_WME"].abs() > 0.001]
    elif show == "Fără diferență":
        selected = selected[selected["Diferenta_WMS_minus_WME"].abs() <= 0.001]
    if warehouse_filter != "Toate gestiunile":
        selected = selected[selected["Gestiune"] == warehouse_filter]
    if search.strip():
        query = search.strip()
        mask = selected["CodArticol"].str.contains(query, case=False, regex=False, na=False)
        mask |= selected["DenumireArticol"].astype("string").str.contains(
            query, case=False, regex=False, na=False
        )
        mask |= selected["Gestiune"].str.contains(query, case=False, regex=False, na=False)
        selected = selected[mask]

    # Registry evidence is shown as a run count, not as human approval.
    try:
        history_rows = list_generated_reports()
        run_counts = pd.Series([h["product_code"] for h in history_rows]).value_counts().to_dict()
    except (OSError, ValueError):
        history_rows = []
        run_counts = {}
        st.warning("Registrul verificărilor este temporar indisponibil.")
    selected = selected.copy()
    selected["Rapoarte generate"] = selected["CodArticol"].map(run_counts).fillna(0).astype(int)
    latest_statuses = latest_operator_statuses()
    selected["Status operator"] = [
        latest_statuses.get((str(row.CodArticol), str(row.Gestiune)), {}).get("status", "NEVERIFICAT")
        for row in selected.itertuples(index=False)
    ]
    st.dataframe(selected, use_container_width=True, hide_index=True, height=420)

    if selected.empty:
        st.info("Nicio poziție produs–gestiune pentru filtrele selectate.")
        return

    # Article selection and warehouse scope are independent.
    codes = sorted(selected["CodArticol"].dropna().astype(str).unique().tolist())
    code = st.selectbox("3. Selectează articolul", codes)
    article_positions = warehouse_table[warehouse_table["CodArticol"].astype(str) == code]
    warehouse_options = sorted(article_positions["Gestiune"].dropna().astype(str).unique().tolist())
    chosen_warehouse = st.selectbox(
        "4. Selectează gestiunea / perimetrul",
        ["Toate gestiunile", *warehouse_options],
    )
    total = table.loc[table["CodArticol"].astype(str) == code].iloc[0]
    if chosen_warehouse == "Toate gestiunile":
        st.dataframe(article_positions, use_container_width=True, hide_index=True)
        st.info(
            f"TOTAL ARTICOL {code}: WMS {total['WMS']:,.3f}; "
            f"WME {total['WME']:,.3f}; "
            f"diferență {total['Diferenta_WMS_minus_WME']:+,.3f}. "
            "Analiza motorului acoperă întreg articolul."
        )
    else:
        position = article_positions.loc[article_positions["Gestiune"].astype(str) == chosen_warehouse].iloc[0]
        st.info(
            f"GESTIUNE {chosen_warehouse} / articol {code}: "
            f"WMS {position['WMS']:,.3f}; WME {position['WME']:,.3f}; "
            f"diferență {position['Diferenta_WMS_minus_WME']:+,.3f}. "
            f"TOTAL ARTICOL: diferență {total['Diferenta_WMS_minus_WME']:+,.3f}. "
            "Motorul investighează în continuare toate gestiunile; "
            "selecția individuală este pentru vizualizare și status."
        )
    st.caption(
        "Statusurile pe gestiuni sunt independente. 'Toate gestiunile' "
        "nu este o gestiune fizică și nu primește un status comun automat."
    )
    # Status decisions always reference one real warehouse, including when the
    # stock investigation is displayed for all warehouses.
    status_warehouse = (
        st.selectbox(
            "Gestiunea pentru statusul operatorului",
            warehouse_options,
            help="Investigația rămâne integrală; statusul se salvează numai în gestiunea aleasă.",
        )
        if chosen_warehouse == "Toate gestiunile"
        else chosen_warehouse
    )
    with st.expander("Status operator — decizie umană", expanded=True):
        current = latest_statuses.get((str(code), str(status_warehouse)), {})
        st.caption(f"Status actual: {current.get('status', 'NEVERIFICAT')}. Această decizie nu schimbă verdictul motorului.")
        with st.form(key=f"decision_{code}_{status_warehouse}"):
            operator_user = st.text_input("Utilizator operator", value="", key=f"user_{code}_{status_warehouse}")
            status_choice = st.selectbox("Status nou", [value for value in STATUSES if value != "NEVERIFICAT"])
            observation = st.text_area("Observație / justificare")
            relevant_reports = [h for h in history_rows if h["product_code"] == str(code)]
            report_lookup = {h["run_id"]: h for h in relevant_reports}
            report_choices = ["Fără raport", *[h["run_id"] for h in relevant_reports]]
            report_run_id = st.selectbox(
                "Raport TraceAI asociat — cel mai recent este propus automat",
                report_choices,
                format_func=lambda rid: (
                    "Fără raport" if rid == "Fără raport" else
                    f"{report_lookup[rid]['recorded_at']} | {report_lookup[rid]['period']} | "
                    f"dif. {report_lookup[rid]['difference']} {report_lookup[rid]['unit']} | "
                    f"{report_lookup[rid]['engine_verdict']} | ID {rid}"
                ),
                index=1 if len(report_choices) > 1 else 0,
            )
            confirm_report = st.checkbox("Confirm că am identificat și verificat raportul selectat")
            save_decision = st.form_submit_button("Salvează statusul")
        if report_run_id != "Fără raport":
            report_selected = report_lookup[report_run_id]
            st.caption(
                f"Raportul investighează întreg articolul {code}, nu exclusiv "
                f"gestiunea {status_warehouse}. Perioadă: {report_selected['period']}; "
                f"verdict motor: {report_selected['engine_verdict']}; "
                f"diferență total articol: {report_selected['difference']} {report_selected['unit']}."
            )
            report_document = Path(report_selected["docx_path"])
            if report_document.is_file():
                st.download_button(
                    "Descarcă raportul selectat",
                    data=report_document.read_bytes(),
                    file_name=report_filename(code, report_run_id, "docx"),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"selected_doc_{code}_{status_warehouse}_{report_run_id}",
                )
            else:
                st.error("Raportul selectat nu mai există în arhivă.")
        if save_decision:
            try:
                if report_run_id != "Fără raport" and not confirm_report:
                    raise ValueError("Confirmă explicit raportul asociat înainte de salvare.")
                if report_run_id != "Fără raport" and not Path(report_lookup[report_run_id]["docx_path"]).is_file():
                    raise ValueError("Raportul arhivat nu mai există.")
                event_id = set_operator_status(
                    product_code=str(code), warehouse=str(status_warehouse),
                    status=status_choice, operator_user=operator_user,
                    observation=observation,
                    report_run_id=report_run_id if report_run_id != "Fără raport" else None,
                )
                st.success(f"Decizie salvată în registru: {event_id[:12]}")
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(f"Statusul nu a fost salvat: {exc}")
    with st.expander("Perimetru informativ — Depozitare și Recepție nerelocată"):
        consolidated = build_depozitare_consolidated_view(warehouse_table)
        st.dataframe(
            consolidated[consolidated["CodArticol"] == code],
            use_container_width=True, hide_index=True,
        )
    st.caption("Statusul operatorului este decizie explicită, înregistrată separat de verdictul motorului.")
    from traceai_reconciliation.investigation.human_evidence import HumanAttestation
    import json
    human_attestations = []
    with st.expander("Confirmare umană ajustare WMS (opțional)"):
        reports_for_product = [x for x in history_rows if x["product_code"] == str(code)]
        events = []
        if reports_for_product:
            try:
                payload = json.loads(Path(reports_for_product[0]["json_path"]).read_text(encoding="utf-8"))
                events = [e for e in payload.get("case_report", {}).get("operation_timeline", [])
                          if e.get("system") == "WMS"
                          and e.get("operation_type") in ("Ajustare negativa", "Ajustare pozitiva")
                          and e.get("source_row") is not None]
            except (OSError, ValueError, TypeError):
                st.warning("Raportul arhivat nu poate fi citit.")
        if events:
            idx = st.selectbox("Rând WMS", range(len(events)),
                               format_func=lambda i: f"{events[i]['date']} | {events[i]['source_row']} | {events[i]['quantity']}")
            e = events[idx]
            physical = st.checkbox("Verificarea fizică a fost efectuată")
            wme_absent = st.checkbox("Nu a fost efectuată ajustare WME")
            note = st.text_input("Declarație / motiv")
            verifier = st.text_input("Persoana care confirmă")
            authorize = st.checkbox("Confirm exclusiv acest rând; fără MATCH sau ajustare automată")
            if physical and wme_absent and note.strip() and verifier.strip() and authorize:
                human_attestations = [HumanAttestation(
                    evidence_id=f"HUM-{code}-{e['source_row']}", product_code=str(code),
                    system="WMS", source_row=int(e["source_row"]),
                    source_date=str(e["date"])[:10], signed_quantity=float(e["quantity"]),
                    unit=str(payload.get("investigation", {}).get("unit") or ""),
                    physical_count_confirmed=True, counterpart_wme_exists=False,
                    statement=note.strip(), provenance=f"Streamlit: {verifier.strip()}")]
                st.caption("Validarea va fi recontrolată pe sursa WMS curentă.")
        else:
            st.info("Rulează întâi o investigație pentru a identifica ajustările WMS.")
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
                human_attestations=human_attestations,
            )
        except Exception as exc:
            st.error(f"Analiza este blocată și nu se declară MATCH: {type(exc).__name__}: {exc}")
            return
    try:
        saved_run_id = record_generated_report(result.summary_json)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Raportul a fost generat, dar NU a fost arhivat în registru: {exc}")
        return
    st.success(f"Investigația a fost arhivată în registru: {saved_run_id}. Verdictul nu reprezintă aprobare.")

    case_dir = workspace / "cases" / f"CASE-SELF-{code}"
    docx = case_dir / "case.docx"
    json_file = case_dir / "case.json"
    for file, label, mime in [
        (docx, "Descarcă raport DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (json_file, "Descarcă dovezi JSON", "application/json"),
    ]:
        if file.is_file():
            st.download_button(label, data=file.read_bytes(), file_name=report_filename(code, saved_run_id, file.suffix.lstrip(".")), mime=mime)
    st.info("Documentele pot conține REVIEW. Corecțiile de stoc sunt decise și efectuate exclusiv de operator.")


if __name__ == "__main__":
    main()
