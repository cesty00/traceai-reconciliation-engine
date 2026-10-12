from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from traceai_reconciliation.loaders import read_table
from traceai_reconciliation.product_audit import summarize_stock_report

from .batch import BatchCaseSpec


@dataclass(frozen=True, slots=True)
class DailyDeltaItem:
    case_id: str
    product_code: str
    status: str
    previous_difference: float | None
    current_difference: float | None
    difference_delta: float | None
    execution_policy: str
    note: str


@dataclass(frozen=True, slots=True)
class DailyDeltaSummary:
    previous_run_id: str | None
    new: int
    changed: int
    unchanged: int
    items: tuple[DailyDeltaItem, ...]


def build_snapshot_state(
    stock_report: str | Path,
    cases: list[BatchCaseSpec],
) -> dict[str, dict[str, Any]]:
    """
    Build a lightweight per-case state from the stock snapshot.

    This intentionally does not claim operational equivalence. Equal final stock
    differences are useful for prioritisation, but they are not sufficient to
    skip reconciliation when movement-source identities changed.
    """
    frame = read_table(stock_report)
    state: dict[str, dict[str, Any]] = {}
    for case in cases:
        audit = summarize_stock_report(frame, case.product_code)
        state[case.case_id] = {
            "case_id": case.case_id,
            "product_code": case.product_code,
            "product_name": audit.product_name,
            "reported_stock_wms": audit.reported_stock_wms,
            "reported_stock_wme": audit.reported_stock_wme,
            "difference_reported": audit.difference_reported,
        }
    return state


def find_previous_run_manifest(
    output_root: str | Path,
    current_run_id: str,
) -> Path | None:
    root = Path(output_root)
    if not root.exists():
        return None

    candidates: list[tuple[float, Path]] = []
    for child in root.iterdir():
        if not child.is_dir() or child.name == current_run_id.replace("/", "_"):
            continue
        manifest = child / "run_manifest.json"
        summary = child / "daily_run_summary.json"
        if not manifest.exists() or not summary.exists():
            continue
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "FAILED_SAFE":
            continue
        candidates.append((summary.stat().st_mtime, manifest))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def load_previous_snapshot_state(
    manifest_path: str | Path | None,
) -> tuple[str | None, dict[str, dict[str, Any]]]:
    if manifest_path is None:
        return None, {}
    path = Path(manifest_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, {}

    run_id = str(payload.get("run_id") or "").strip() or None
    state = payload.get("snapshot_state")
    if not isinstance(state, dict):
        return run_id, {}
    return run_id, {
        str(key): value
        for key, value in state.items()
        if isinstance(value, dict)
    }


def classify_snapshot_delta(
    *,
    current_state: dict[str, dict[str, Any]],
    previous_state: dict[str, dict[str, Any]],
    source_hashes_changed: bool,
    tolerance: float = 1e-9,
    previous_run_id: str | None = None,
) -> DailyDeltaSummary:
    items: list[DailyDeltaItem] = []

    for case_id, current in current_state.items():
        product_code = str(current.get("product_code") or "")
        current_diff = float(current.get("difference_reported") or 0.0)
        previous = previous_state.get(case_id)

        if previous is None:
            status = "NEW"
            previous_diff = None
            delta = None
            policy = "ANALYZE"
            note = "Case not present in previous successful daily snapshot."
        else:
            previous_diff = float(previous.get("difference_reported") or 0.0)
            delta = current_diff - previous_diff
            if abs(delta) <= tolerance:
                status = "UNCHANGED"
                if source_hashes_changed:
                    policy = "REANALYZE_SOURCE_CHANGED"
                    note = (
                        "Final stock difference is unchanged, but at least one "
                        "source identity changed; safe reuse is not allowed."
                    )
                else:
                    policy = "REUSE_SAFE"
                    note = (
                        "Final stock difference and all source identities are "
                        "unchanged."
                    )
            else:
                status = "CHANGED"
                policy = "ANALYZE"
                note = "Final stock difference changed since previous daily run."

        items.append(
            DailyDeltaItem(
                case_id=case_id,
                product_code=product_code,
                status=status,
                previous_difference=previous_diff,
                current_difference=current_diff,
                difference_delta=delta,
                execution_policy=policy,
                note=note,
            )
        )

    return DailyDeltaSummary(
        previous_run_id=previous_run_id,
        new=sum(item.status == "NEW" for item in items),
        changed=sum(item.status == "CHANGED" for item in items),
        unchanged=sum(item.status == "UNCHANGED" for item in items),
        items=tuple(items),
    )


def delta_payload(summary: DailyDeltaSummary) -> dict[str, Any]:
    return asdict(summary)
