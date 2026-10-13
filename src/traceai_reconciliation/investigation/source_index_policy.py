from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import InvestigationSources
from .source_index import SQLiteSourceIndex


@dataclass(frozen=True, slots=True)
class SourceIndexResolution:
    index: SQLiteSourceIndex | None
    details: dict[str, Any]


def resolve_source_index(
    sources: InvestigationSources,
) -> SourceIndexResolution:
    """Create and refresh the operational source index when explicitly enabled."""
    if not sources.use_source_index:
        return SourceIndexResolution(
            index=None,
            details={
                "enabled": False,
                "rebuilt": False,
            },
        )

    if sources.cache_dir is None:
        raise ValueError(
            "use_source_index=True necesită cache_dir."
        )

    source_index = SQLiteSourceIndex(sources.cache_dir)
    rebuilt = source_index.ensure_index(
        sources.wms_movements,
        sources.wme_ledger,
        sources.production,
    )
    return SourceIndexResolution(
        index=source_index,
        details={
            "enabled": True,
            "rebuilt": rebuilt,
            "database": str(source_index.db_path),
        },
    )
