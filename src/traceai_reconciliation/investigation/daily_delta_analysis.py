from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .daily_delta import DailyDeltaSummary
from .delta_movement_window import build_delta_movement_window
from .delta_root_cause import analyze_delta_root_cause
from .models import InvestigationSources
from .source_index import SQLiteSourceIndex


@dataclass(frozen=True, slots=True)
class DailyDeltaRootCauseItem:
    case_id: str
    product_code: str
    status: str
    reason: str
    analysis: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class DailyDeltaRootCauseSummary:
    previous_snapshot_at: str | None
    current_snapshot_at: str | None
    analyzed: int
    skipped: int
    exact_event: int
    multi_event: int
    unexplained: int
    items: tuple[DailyDeltaRootCauseItem, ...]


def analyze_daily_delta_root_causes(
    *,
    delta: DailyDeltaSummary,
    current_snapshot_state: dict[str, dict[str, Any]],
    previous_snapshot_at: str | None,
    current_snapshot_at: str | None,
    sources: InvestigationSources,
) -> DailyDeltaRootCauseSummary:
    """Analyze CHANGED daily cases only when exact snapshot bounds are known.

    Missing snapshot timestamps are not guessed from run time or file mtime.
    The analyzer skips causal attribution rather than creating false precision.
    """
    changed = [item for item in delta.items if item.status == "CHANGED"]
    if not changed:
        return DailyDeltaRootCauseSummary(
            previous_snapshot_at=previous_snapshot_at,
            current_snapshot_at=current_snapshot_at,
            analyzed=0,
            skipped=0,
            exact_event=0,
            multi_event=0,
            unexplained=0,
            items=(),
        )

    if not previous_snapshot_at or not current_snapshot_at:
        items = tuple(
            DailyDeltaRootCauseItem(
                case_id=item.case_id,
                product_code=item.product_code,
                status="SKIPPED",
                reason="SNAPSHOT_TIME_MISSING",
            )
            for item in changed
        )
        return DailyDeltaRootCauseSummary(
            previous_snapshot_at=previous_snapshot_at,
            current_snapshot_at=current_snapshot_at,
            analyzed=0,
            skipped=len(items),
            exact_event=0,
            multi_event=0,
            unexplained=0,
            items=items,
        )

    if not sources.use_source_index or sources.cache_dir is None:
        items = tuple(
            DailyDeltaRootCauseItem(
                case_id=item.case_id,
                product_code=item.product_code,
                status="SKIPPED",
                reason="SOURCE_INDEX_DISABLED",
            )
            for item in changed
        )
        return DailyDeltaRootCauseSummary(
            previous_snapshot_at=previous_snapshot_at,
            current_snapshot_at=current_snapshot_at,
            analyzed=0,
            skipped=len(items),
            exact_event=0,
            multi_event=0,
            unexplained=0,
            items=items,
        )

    index = SQLiteSourceIndex(sources.cache_dir)
    index.ensure_index(
        sources.wms_movements,
        sources.wme_ledger,
        sources.production,
    )

    results: list[DailyDeltaRootCauseItem] = []
    for item in changed:
        current = current_snapshot_state.get(item.case_id, {})
        product_name = str(current.get("product_name") or "").strip()
        if not product_name:
            results.append(
                DailyDeltaRootCauseItem(
                    case_id=item.case_id,
                    product_code=item.product_code,
                    status="SKIPPED",
                    reason="PRODUCT_NAME_MISSING",
                )
            )
            continue

        if (
            item.previous_difference is None
            or item.current_difference is None
        ):
            results.append(
                DailyDeltaRootCauseItem(
                    case_id=item.case_id,
                    product_code=item.product_code,
                    status="SKIPPED",
                    reason="DIFFERENCE_BOUNDARY_MISSING",
                )
            )
            continue

        movement_window = build_delta_movement_window(
            source_index=index,
            product_code=item.product_code,
            product_name=product_name,
            start_exclusive=previous_snapshot_at,
            end_inclusive=current_snapshot_at,
        )
        # Stock report totals do not prove which warehouses were included.
        # Do not pass AGGREGATE based on a total alone: a transfer can affect
        # one-warehouse stock while leaving company-wide stock unchanged.
        scope = (
            "AGGREGATE"
            if current.get("stock_scope") == "AGGREGATE"
            and current.get("stock_scope_verified") is True
            else None
        )
        root_cause = analyze_delta_root_cause(
            movement_window=movement_window,
            previous_difference=item.previous_difference,
            current_difference=item.current_difference,
            stock_scope=scope,
        )
        results.append(
            DailyDeltaRootCauseItem(
                case_id=item.case_id,
                product_code=item.product_code,
                status=root_cause.status,
                reason="ANALYZED",
                analysis={
                    "movement_window": asdict(movement_window),
                    "root_cause": asdict(root_cause),
                },
            )
        )

    return DailyDeltaRootCauseSummary(
        previous_snapshot_at=previous_snapshot_at,
        current_snapshot_at=current_snapshot_at,
        analyzed=sum(item.reason == "ANALYZED" for item in results),
        skipped=sum(item.status == "SKIPPED" for item in results),
        exact_event=sum(item.status == "EXACT_EVENT" for item in results),
        multi_event=sum(item.status == "MULTI_EVENT" for item in results),
        unexplained=sum(item.status == "UNEXPLAINED" for item in results),
        items=tuple(results),
    )
