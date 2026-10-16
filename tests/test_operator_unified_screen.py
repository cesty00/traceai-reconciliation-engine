import ast
from pathlib import Path

def test_unified_operator_screen_contract():
    root=Path(__file__).resolve().parents[1]
    source=(root/"operator_app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'Raport unic de stoc — produs + gestiune' in source
    assert 'selected = warehouse_table.copy()' in source
    assert 'code = st.selectbox("3. Selectează articolul", codes)' in source
    assert '"4. Selectează gestiunea / perimetrul"' in source
    assert '["Toate gestiunile", *warehouse_options]' in source
    assert 'total = table.loc[table["CodArticol"].astype(str) == code].iloc[0]' in source
    assert 'product_code=code' in source
    assert 'latest_operator_statuses()' in source
    assert 'selected["Status operator"]' in source
    assert 'set_operator_status(' in source


def test_status_panel_visible_in_all_warehouses_mode():
    source=(Path(__file__).resolve().parents[1]/"operator_app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert '"Gestiunea pentru statusul operatorului"' in source
    assert 'if chosen_warehouse == "Toate gestiunile"' in source
    assert 'with st.expander("Status operator — decizie umană", expanded=True):' in source
    assert 'warehouse=str(status_warehouse)' in source
    assert 'if chosen_warehouse != "Toate gestiunile":\n        with st.expander("Status operator' not in source
