from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path
from typing import Any

from traceai_reconciliation import __version__
from traceai_reconciliation.run_store import SQLiteRunStore
from traceai_reconciliation.investigation.daily_case_summary import (
    validate_daily_case_summary_contract,
)


_REQUIRED_AUTHORITY = {
    "human_decision_required": True,
    "automatic_approval_allowed": False,
    "registry_apply_allowed": False,
    "wms_mutation_allowed": False,
    "wme_mutation_allowed": False,
}

_REQUIRED_SOURCE_TYPES = {
    "stock_report",
    "opening_stock_wms",
    "wms_movements",
    "wme_ledger",
    "production",
    "nomenclature",
}


@dataclass(frozen=True, slots=True)
class PilotAcceptanceResult:
    accepted: bool
    run_id: str | None
    engine_version: str
    checked_cases: int
    blockers: tuple[str, ...]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object.")
    return payload


def evaluate_pilot_run(
    summary_path: str | Path,
) -> PilotAcceptanceResult:
    """Validate a completed DAILY run for controlled internal pilot acceptance."""
    path = Path(summary_path)
    blockers: list[str] = []

    if not path.is_file():
        return PilotAcceptanceResult(
            accepted=False,
            run_id=None,
            engine_version=__version__,
            checked_cases=0,
            blockers=(f"missing:daily_run_summary:{path}",),
        )

    try:
        summary = _load_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return PilotAcceptanceResult(
            accepted=False,
            run_id=None,
            engine_version=__version__,
            checked_cases=0,
            blockers=(f"invalid:daily_run_summary:{exc}",),
        )

    run_id = str(summary.get("run_id") or "").strip() or None
    status = str(summary.get("status") or "").strip()
    if status not in {"SUCCESS", "SUCCESS_WITH_REVIEW"}:
        blockers.append(f"run_status:{status or 'MISSING'}")

    if int(summary.get("error") or 0) != 0:
        blockers.append(f"run_errors:{summary.get('error')}")

    if not str(summary.get("signature") or "").strip():
        blockers.append("missing:signature")

    source_hashes = summary.get("source_hashes")
    if not isinstance(source_hashes, dict):
        blockers.append("invalid:source_hashes")
    else:
        missing_sources = sorted(
            _REQUIRED_SOURCE_TYPES - set(source_hashes)
        )
        if missing_sources:
            blockers.append(
                "missing:source_hashes:" + ",".join(missing_sources)
            )

    manifest_path = Path(str(summary.get("run_manifest_json") or ""))
    if not manifest_path.is_file():
        blockers.append("missing:run_manifest")
        manifest: dict[str, Any] = {}
    else:
        try:
            manifest = _load_json(manifest_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            blockers.append(f"invalid:run_manifest:{exc}")
            manifest = {}

    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        blockers.append("invalid:authority")
    else:
        for key, expected in _REQUIRED_AUTHORITY.items():
            if authority.get(key) is not expected:
                blockers.append(f"authority:{key}")

    profile = manifest.get("profile")
    if not isinstance(profile, dict):
        blockers.append("invalid:profile")
    elif not str(profile.get("snapshot_at") or "").strip():
        blockers.append("missing:snapshot_at")

    output_dir = Path(str(summary.get("output_dir") or ""))
    cases_root = output_dir / "cases"
    manifest_cases = manifest.get("cases")
    if not isinstance(manifest_cases, list):
        blockers.append("invalid:manifest_cases")
        enabled_cases: list[dict[str, Any]] = []
    else:
        enabled_cases = [
            item
            for item in manifest_cases
            if isinstance(item, dict) and item.get("enabled", True)
        ]

    checked_cases = 0
    for item in enabled_cases:
        case_id = str(item.get("case_id") or "").strip()
        if not case_id:
            blockers.append("invalid:case_id")
            continue
        checked_cases += 1
        case_dir = cases_root / case_id.replace("/", "_")
        summary_file = case_dir / "daily_case_summary.json"
        if not summary_file.is_file():
            blockers.append(f"{case_id}:missing:daily_case_summary.json")
            continue
        try:
            case_payload = _load_json(summary_file)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            blockers.append(f"{case_id}:invalid:daily_case_summary:{exc}")
            continue
        violations = validate_daily_case_summary_contract(case_payload)
        blockers.extend(
            f"{case_id}:contract:{violation}"
            for violation in violations
        )

        history = case_payload.get("history")
        if isinstance(history, dict):
            recent_runs = history.get("recent_runs")
            if isinstance(recent_runs, list):
                for point in recent_runs:
                    if not isinstance(point, dict):
                        continue
                    if (
                        str(point.get("run_id") or "").strip() == str(run_id or "")
                        and str(point.get("run_status") or "").strip() == "RUNNING"
                    ):
                        blockers.append(
                            f"{case_id}:history:current_run_status=RUNNING"
                        )

    if enabled_cases and checked_cases != len(enabled_cases):
        blockers.append(
            f"case_count:expected={len(enabled_cases)}:checked={checked_cases}"
        )

    store_path = output_dir.parent / ".traceai_state.sqlite"
    if not store_path.is_file():
        blockers.append("missing:run_store")
    elif run_id:
        store = SQLiteRunStore(store_path)
        persisted = store.get_run(run_id)
        if persisted is None:
            blockers.append(f"run_store:missing_run:{run_id}")
        else:
            if persisted.get("status") != status:
                blockers.append(
                    "run_store:status_mismatch:"
                    f"summary={status}:store={persisted.get('status')}"
                )
            if str(persisted.get("engine_version") or "") != __version__:
                blockers.append(
                    "run_store:engine_version_mismatch:"
                    f"store={persisted.get('engine_version')}:current={__version__}"
                )
            if not str(persisted.get("snapshot_at") or "").strip():
                blockers.append("run_store:missing_snapshot_at")

    return PilotAcceptanceResult(
        accepted=not blockers,
        run_id=run_id,
        engine_version=__version__,
        checked_cases=checked_cases,
        blockers=tuple(blockers),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a completed TraceAI DAILY run for controlled "
            "internal pilot acceptance."
        )
    )
    parser.add_argument(
        "daily_run_summary",
        help="Path to daily_run_summary.json from the completed pilot run",
    )
    args = parser.parse_args()

    result = evaluate_pilot_run(args.daily_run_summary)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.accepted else 1)


if __name__ == "__main__":
    main()
