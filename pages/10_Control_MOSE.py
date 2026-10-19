"""Separate read-only MOSE operator panel.

Run through Streamlit multipage navigation under pages/.
Only accepts exported review-queue JSON, not invented case records.
"""
from __future__ import annotations

import json
from pathlib import Path
import streamlit as st
from traceai_reconciliation.mose_control.index_auto_review import create_review_cases_from_existing_index
from traceai_reconciliation.mose_control.mose_source_index import MOSESQLiteSourceIndex
from traceai_reconciliation.mose_control.dossier_from_index import dossier_from_current_index
from traceai_reconciliation.mose_control.review_import import validate_review_cases

st.set_page_config(page_title="TraceAI — Control MOSE", layout="wide")
st.title("TraceAI Control — Control MOSE")
st.caption("Pilot separat · read-only · verdict motor si decizie operator distincte")
st.warning("Sectiune pilot: cazurile trebuie generate din surse reale; niciun MATCH sau corectie WMS/WME automata.")
with st.expander("Generare automata din indexul local WMS/WME", expanded=True):
    st.caption("Se reutilizeaza indexul verificat TraceAI. Sursele locale raman pe calculator.")
    cache_dir = st.text_input("Folder cache index TraceAI", key="mose_cache")
    wms_path = st.text_input("Cale export WMS CSV", key="mose_wms")
    wme_path = st.text_input("Cale fisa magazie WME XLSX", key="mose_wme")
    st.caption("Controlul MOSE necesita numai exporturile WMS si WME; raportul de productie nu este necesar.")
    if st.button("Genereaza cazuri MOSE din sursele locale"):
        if not all((cache_dir.strip(), wms_path.strip(), wme_path.strip())):
            st.error("Completeaza cele trei cai: index, WMS si WME.")
        else:
            try:
                MOSESQLiteSourceIndex(Path(cache_dir).expanduser()).ensure_mose_index(
                    Path(wms_path).expanduser(), Path(wme_path).expanduser())
                result = create_review_cases_from_existing_index(
                    cache_dir=Path(cache_dir).expanduser(),
                    wms_path=Path(wms_path).expanduser(),
                    wme_path=Path(wme_path).expanduser(),
                )
                st.session_state["mose_auto_result"] = result
            except (ValueError, OSError) as exc:
                st.error(f"Generarea MOSE a fost blocata: {exc}")
auto_result = st.session_state.get("mose_auto_result")
if auto_result is not None:
    st.write("Status generare:", auto_result.get("status"))
    st.caption(auto_result.get("limitations", "Diagnosticul ramane REVIEW."))
uploaded = st.file_uploader("Alternativ: importa lista investigatii MOSE (JSON)", type=["json"])
if uploaded is None and not (auto_result and auto_result.get("status") == "WME_CROSS_WAREHOUSE_SCREEN_REVIEW"):
    st.info("Genereaza cazuri din indexul TraceAI sau importa un JSON existent.")
else:
    try:
        if uploaded is not None:
            if uploaded.size > 5 * 1024 * 1024:
                raise ValueError("JSON prea mare (maxim 5 MB)")
            cases = validate_review_cases(json.loads(uploaded.getvalue().decode("utf-8")))
        else:
            cases = validate_review_cases(auto_result["cases"])
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        st.error(f"Fisier invalid: {exc}")
        st.stop()
    if not cases:
        st.info("Nu exista investigatii in fisier.")
        st.stop()
    names = [item["case_id"] for item in cases]
    selected = st.selectbox("Alege investigatia", names)
    case = next(item for item in cases if item["case_id"] == selected)
    st.subheader(f"Document {case.get('document', '-')}")
    st.warning(f"Verdict motor: {case['engine_verdict']} — {case.get('reason', '-')}")
    st.write("Status operator: AWAITING_DOCUMENT_CHECK")
    st.write("Randuri WME originale:", case["evidence_source_rows"])
    st.write("Dovezi:", case.get("facts") or {})
    st.markdown("**Documente si verificari necesare:**")
    for step in case.get("required_checks", []):
        st.write("- " + str(step))
    st.caption("Operatorul verifica documentele in sistemele originale. Acest panou nu inregistreaza confirmari si nu modifica stocul.")
    if (uploaded is None and auto_result is not None and
            auto_result.get("status") == "WME_CROSS_WAREHOUSE_SCREEN_REVIEW"):
        if st.button("Deschide fisa documentara din sursele locale", key="mose_dossier"):
            dossier = dossier_from_current_index(
                case=case, cache_dir=Path(cache_dir).expanduser(),
                wms_path=Path(wms_path).expanduser(),
                wme_path=Path(wme_path).expanduser(),
            )
            st.session_state["mose_dossier_result"] = dossier
            st.session_state["mose_dossier_case"] = selected
        if st.session_state.get("mose_dossier_case") == selected:
            dossier = st.session_state.get("mose_dossier_result")
            if dossier:
                st.write("Stare fisa:", dossier["status"])
                if dossier.get("status") == "AWAITING_OPERATOR_DOCUMENT_CHECK":
                    if dossier.get("direct_dp_delivery_review"):
                        st.subheader("Facturare directa DP — verificare livrare WMS")
                        st.json(dossier["direct_dp_delivery_review"])
                    if dossier.get("document_link_audit"):
                        st.subheader("Comenzi WMS candidate — asociere factura neconfirmata")
                        st.dataframe(dossier["document_link_audit"].get("customer_order_candidates", []))
                    if dossier.get("quantity_candidate_audit"):
                        st.subheader("Cantitati factura vs livrari WMS candidate — nu MATCH")
                        st.dataframe(dossier["quantity_candidate_audit"].get("items", []))
                    if dossier.get("generic_evidence_audit"):
                        st.subheader("Control documentar general — doar REVIEW")
                        st.json(dossier["generic_evidence_audit"]["checks"])
                    if dossier.get("reference_acceptance"):
                        audit = dossier["reference_acceptance"]
                        st.info(f"Control referinte documentare: {audit['status']} — nu MATCH")
                        if audit.get("missing"):
                            st.warning("Referinte lipsa: " + ", ".join(audit["missing"]))
                    st.subheader("Linii factura WME")
                    st.dataframe(dossier["wme_invoices_source_evidence"], use_container_width=True)
                    st.subheader("Transferuri WMS candidate — nu MATCH")
                    st.dataframe(dossier["wms_transfer_candidates_unverified"], use_container_width=True)
                    st.subheader("Livrari directe WMS candidate — nu MATCH")
                    matching_partner = [row for row in dossier["wms_delivery_candidates_unverified"]
                                        if row.get("partner_screen") == "PARTNER_CANDIDATE"]
                    other_partner = [row for row in dossier["wms_delivery_candidates_unverified"]
                                     if row.get("partner_screen") != "PARTNER_CANDIDATE"]
                    st.dataframe(matching_partner, use_container_width=True)
                    if other_partner:
                        st.warning("Exista livrari catre alti parteneri sau cu partener neverificat. Nu sunt corespondente confirmate ale facturii.")
                        with st.expander("Livrari catre alti parteneri / neverificate"):
                            st.dataframe(other_partner, use_container_width=True)
                    if dossier.get("wms_candidate_screen_truncated"):
                        st.warning("Lista WMS a fost limitata; absenta unui document nu poate fi concluzionata.")
                    st.subheader("NT WME candidate (neconfirmate)")
                    st.dataframe(dossier["wme_nt_candidates_unverified"], use_container_width=True)
                    if dossier.get("nt_candidate_screen_truncated"):
                        st.warning("Lista NT este incompleta: sunt mai multe documente decat limita de afisare.")
                    st.subheader("Sold inainte/dupa fiecare linie F — WME (aritmetic)")
                    st.dataframe(dossier.get("invoice_balance_evidence", {}).get("records", []), use_container_width=True)
                    st.caption("Sold anterior dedus matematic; NU certifica stocul fizic, lotul sau corectitudinea gestiunii.")
                    st.write("Solduri WME raportate (scope nevalidat)",
                             dossier["wme_observed_balances_unverified_scope"])
                    st.caption("Legatura NT↔WMS si soldul final raman NOT_VERIFIED.")

