import ast
from pathlib import Path

def test_report_selection_and_confirmation_contract():
    source=(Path(__file__).resolve().parents[1]/"operator_app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'relevant_reports = [h for h in history_rows if h["product_code"] == str(code)]' in source
    assert 'index=1 if len(report_choices) > 1 else 0' in source
    assert 'Confirm că am identificat și verificat raportul selectat' in source
    assert 'Confirmă explicit raportul asociat înainte de salvare.' in source
    assert 'Raportul investighează întreg articolul' in source
    assert 'report_run_id=report_run_id if report_run_id != "Fără raport" else None' in source
