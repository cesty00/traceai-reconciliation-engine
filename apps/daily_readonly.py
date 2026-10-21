"""TraceAI Daily read-only preview. Run with: streamlit run apps/daily_readonly.py -- --case path/to/daily_operator_result.json
No reviewer submissions, logins or WMS/WME writes.
"""
import argparse
import json
from pathlib import Path
import streamlit as st
from traceai_reconciliation.daily_ui.read_model import operator_view

parser=argparse.ArgumentParser(add_help=False)
parser.add_argument("--case")
args,_=parser.parse_known_args()
st.set_page_config(page_title="TraceAI Daily — read-only",layout="wide")
st.title("TraceAI Control — Daily")
st.caption("Diagnostic read-only. Fără confirmări de operator sau modificări de stoc.")
if not args.case:
    st.info("Specificați un fișier JSON: streamlit run apps/daily_readonly.py -- --case /cale/daily_operator_result.json")
    st.stop()
try:
    data=json.loads(Path(args.case).read_text(encoding="utf-8"))
    view=operator_view(data)
except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
    st.error("Rezultatul nu poate fi afișat în siguranță: " + str(exc))
    st.stop()
st.subheader(f"{view['product_code']} — {view['product_name']}")
left,mid,right=st.columns(3)
left.metric("Diferență",f"{view['difference']:.3f} {view['unit']}")
mid.metric("Rezidual",f"{view['residual']:.3f} {view['unit']}")
right.metric("Status operator (motor)",view["operator_status"])
st.warning("Validarea documentară nu este activată. Acest status nu reprezintă aprobarea unui evaluator.")
st.write("Cauză:",view["cause"])
st.write("Status cauză:",view["cause_status"])
st.write("Reguli:",", ".join(view["rules"]) or "Nedeterminate")
st.write("Acțiune recomandată:",view["operator_action"])
st.subheader("Dovezi raportate de motor")
st.warning("Referințele la documente și liniile fizice originale NU sunt verificate în acest JSON. Consultați documentele-sursă înainte de validare.")
for item in view["evidence"]:
    st.write("•",item)
if view["blockers"]:
    st.subheader("Blocaje")
    for item in view["blockers"]: st.write("•",item)
if view["warnings"]:
    st.subheader("Avertismente")
    for item in view["warnings"]: st.write("•",item)
st.caption("Fără butoane de aprobare. MATCH economic și modificările WMS/WME nu sunt autorizate.")
