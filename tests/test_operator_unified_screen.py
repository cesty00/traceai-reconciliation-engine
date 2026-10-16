import ast
from pathlib import Path

def test_unified_operator_screen_contract():
    root=Path(__file__).resolve().parents[1]
    source=(root/"operator_app.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert 'Raport unic de stoc — produs + gestiune' in source
    assert 'selected = warehouse_table.copy()' in source
    assert 'code, chosen_warehouse = positions[chosen_position]' in source
    assert 'total = table.loc[table["CodArticol"] == code].iloc[0]' in source
    assert 'product_code=code' in source
    assert 'Status operator"] = "Nesetat — urmează implementarea deciziilor"' in source
