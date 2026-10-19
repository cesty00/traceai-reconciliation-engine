"""Separate read-only MOSE operator panel.

Run through Streamlit multipage navigation under pages/.
Only accepts exported review-queue JSON, not invented case records.
"""
from __future__ import annotations

import json
import streamlit as st
from traceai_reconciliation.mose_control.review_import import validate_review_cases

st.set_page_config(page_title="TraceAI — Control MOSE", layout="wide")
st.title("TraceAI Control — Control MOSE")
st.caption("Pilot separat · read-only · verdict motor si decizie operator distincte")
st.warning("Sectiune pilot: cazurile trebuie generate din surse reale; niciun MATCH sau corectie WMS/WME automata.")
uploaded = st.file_uploader("Importa lista de investigatii MOSE (JSON)", type=["json"])
if uploaded is None:
    st.info("Incarca fisierul JSON generat din review_queue pentru a vedea cazurile. Nu este conectat inca la importul automat WME/WMS.")
else:
    try:
        if uploaded.size > 5 * 1024 * 1024:
            raise ValueError("JSON prea mare (maxim 5 MB)")
        cases = validate_review_cases(json.loads(uploaded.getvalue().decode("utf-8")))
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
