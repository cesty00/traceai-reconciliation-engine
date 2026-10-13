from __future__ import annotations

from pathlib import Path

import pytest

from traceai_reconciliation.investigation.models import InvestigationSources
from traceai_reconciliation.investigation.source_index_policy import (
    resolve_source_index,
)


def _sources(
    tmp_path: Path,
    *,
    use_source_index: bool,
    cache_dir: Path | None,
) -> InvestigationSources:
    return InvestigationSources(
        stock_report=tmp_path / "stock.xlsx",
        opening_stock_wms=tmp_path / "opening.xlsx",
        wms_movements=tmp_path / "wms.csv",
        wme_ledger=tmp_path / "wme.xlsx",
        production=tmp_path / "production.csv",
        nomenclature=tmp_path / "nomenclature.xlsx",
        cache_dir=cache_dir,
        use_source_index=use_source_index,
    )


def test_source_index_disabled_returns_none(tmp_path: Path) -> None:
    result = resolve_source_index(
        _sources(
            tmp_path,
            use_source_index=False,
            cache_dir=None,
        )
    )

    assert result.index is None
    assert result.details == {
        "enabled": False,
        "rebuilt": False,
    }


def test_source_index_enabled_requires_cache_dir(tmp_path: Path) -> None:
    with pytest.raises(
        ValueError,
        match="use_source_index=True necesită cache_dir",
    ):
        resolve_source_index(
            _sources(
                tmp_path,
                use_source_index=True,
                cache_dir=None,
            )
        )


def test_source_index_enabled_refreshes_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}

    class FakeIndex:
        def __init__(self, cache_dir: Path) -> None:
            calls["cache_dir"] = cache_dir
            self.db_path = cache_dir / "operational_sources.sqlite"

        def ensure_index(
            self,
            wms_path: Path,
            wme_path: Path,
            production_path: Path,
        ) -> bool:
            calls["paths"] = (
                wms_path,
                wme_path,
                production_path,
            )
            return True

    monkeypatch.setattr(
        "traceai_reconciliation.investigation.source_index_policy.SQLiteSourceIndex",
        FakeIndex,
    )

    cache_dir = tmp_path / "cache"
    sources = _sources(
        tmp_path,
        use_source_index=True,
        cache_dir=cache_dir,
    )

    result = resolve_source_index(sources)

    assert result.index is not None
    assert calls["cache_dir"] == cache_dir
    assert calls["paths"] == (
        sources.wms_movements,
        sources.wme_ledger,
        sources.production,
    )
    assert result.details == {
        "enabled": True,
        "rebuilt": True,
        "database": str(cache_dir / "operational_sources.sqlite"),
    }
