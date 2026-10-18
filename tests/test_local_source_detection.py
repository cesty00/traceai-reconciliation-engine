from pathlib import Path
import pytest
from traceai_reconciliation.local_source_detection import discover_source_files


def test_six_sources_detected(tmp_path: Path):
    names = ["Raport_stoc_WMS_WME.xlsx", "Stoc_initial_WMS.xlsx",
             "Trasabilitate_WMS.CSV", "Fisa_magazie_WME.XLSX",
             "Rapoarte_productie.CSV", "Nomenclator_mapare_WME_WMS.xlsx"]
    for name in names:
        (tmp_path / name).touch()
    detected, problems = discover_source_files(tmp_path)
    assert len(detected) == 6
    assert not problems


def test_ambiguous_and_missing_sources_do_not_auto_assign(tmp_path: Path):
    (tmp_path / "Trasabilitate_1.CSV").touch()
    (tmp_path / "Trasabilitate_2.CSV").touch()
    detected, problems = discover_source_files(tmp_path)
    assert "wms_movements" not in detected
    assert len(problems["wms_movements"]) == 2
    assert "stock_report" in problems


def test_nonexistent_directory_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="Folderul"):
        discover_source_files(tmp_path / "missing")
