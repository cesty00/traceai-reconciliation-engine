from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


EVIDENCE_RANK = {
    "A": 4,
    "B": 3,
    "C": 2,
    "D": 1,
}


def _number(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0.0
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    elif "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _period(value: object) -> str:
    return str(value or "").strip().replace("–", "-")


def build_registry_apply_plan(
    registry_rows: Iterable[dict[str, Any]],
    batch_summary_path: str | Path,
    *,
    minimum_evidence: str = "B",
    tolerance: float = 0.001,
) -> dict[str, Any]:
    """
    Stage registry updates without applying them.

    A case is SAFE_UPDATE_EXISTING only when the batch payload matches the
    existing registry identity/baseline and the new evidence meets the minimum
    threshold. The function never mutates Google Drive.
    """
    minimum_rank = EVIDENCE_RANK.get(
        minimum_evidence.upper(),
        EVIDENCE_RANK["B"],
    )

    registry_by_case: dict[str, dict[str, Any]] = {}
    for row in registry_rows:
        case_id = str(row.get("CASE_ID", "")).strip()
        if case_id and case_id not in registry_by_case:
            registry_by_case[case_id] = dict(row)

    summary_path = Path(batch_summary_path)
    batch = json.loads(summary_path.read_text(encoding="utf-8"))
    root = summary_path.parent

    items: list[dict[str, Any]] = []

    for case in batch.get("cases", []):
        case_id = str(case.get("case_id", "")).strip()
        product_code = str(case.get("product_code", "")).strip()
        status = str(case.get("status", "")).strip().upper()

        item: dict[str, Any] = {
            "case_id": case_id,
            "product_code": product_code,
            "batch_status": status,
            "action": None,
            "reason": None,
            "registry_update_path": None,
        }

        if status == "ERROR":
            item["action"] = "HOLD_ERROR"
            item["reason"] = case.get("error")
            items.append(item)
            continue

        if status == "SKIPPED":
            item["action"] = "HOLD_SKIPPED"
            item["reason"] = "Case disabled in batch manifest."
            items.append(item)
            continue

        case_dir_value = case.get("case_dir")
        case_dir = (
            Path(case_dir_value)
            if case_dir_value
            else root / case_id
        )
        registry_update_path = case_dir / "registry_update.json"
        item["registry_update_path"] = str(registry_update_path)

        if not registry_update_path.exists():
            item["action"] = "HOLD_MISSING_PAYLOAD"
            item["reason"] = "registry_update.json is missing."
            items.append(item)
            continue

        payload = json.loads(
            registry_update_path.read_text(encoding="utf-8")
        )
        values = payload.get("values", {})

        existing = registry_by_case.get(case_id)
        if existing is None:
            item["action"] = "HOLD_MISSING_CASE"
            item["reason"] = "CASE_ID not found in registry export."
            items.append(item)
            continue

        if str(existing.get("Cod_produs", "")).strip() != str(
            values.get("Cod_produs", "")
        ).strip():
            item["action"] = "HOLD_PRODUCT_MISMATCH"
            item["reason"] = "Product code differs from existing registry row."
            items.append(item)
            continue

        if _period(existing.get("Perioada_WMS")) != _period(
            values.get("Perioada_WMS")
        ):
            item["action"] = "HOLD_PERIOD_MISMATCH"
            item["reason"] = "Investigation period differs from registry row."
            items.append(item)
            continue

        existing_difference = _number(existing.get("Diferenta"))
        proposed_difference = _number(values.get("Diferenta"))
        if abs(existing_difference - proposed_difference) > tolerance:
            item["action"] = "HOLD_DIFFERENCE_MISMATCH"
            item["reason"] = (
                f"Registry difference {existing_difference} vs "
                f"payload {proposed_difference}."
            )
            items.append(item)
            continue

        evidence = str(values.get("Nivel_proba", "")).strip().upper()
        if EVIDENCE_RANK.get(evidence, 0) < minimum_rank:
            item["action"] = "HOLD_EVIDENCE"
            item["reason"] = (
                f"Evidence {evidence or '-'} below minimum "
                f"{minimum_evidence.upper()}."
            )
            items.append(item)
            continue

        proposed_status = str(
            values.get("Status_investigatie", "")
        ).strip().upper()
        if proposed_status not in {
            "IN_ANALIZA",
            "ASTEPTARE_VALIDARE",
        }:
            item["action"] = "HOLD_STATUS"
            item["reason"] = (
                f"Unsupported proposed status {proposed_status or '-'}."
            )
            items.append(item)
            continue

        item["action"] = "SAFE_UPDATE_EXISTING"
        item["reason"] = (
            "CASE_ID/product/period/difference match and evidence threshold met."
        )
        item["proposed"] = {
            "Verdict": values.get("Verdict"),
            "Nivel_proba": values.get("Nivel_proba"),
            "Cauza": values.get("Cauza"),
            "Regula_aplicata": values.get("Regula_aplicata"),
            "Status_investigatie": values.get("Status_investigatie"),
            "Observatii": values.get("Observatii"),
        }
        item["preserve_if_empty"] = payload.get(
            "preserve_if_empty",
            [],
        )
        items.append(item)

    counts: dict[str, int] = {}
    for item in items:
        action = str(item["action"])
        counts[action] = counts.get(action, 0) + 1

    return {
        "schema_version": "1.0",
        "batch_id": batch.get("batch_id"),
        "minimum_evidence": minimum_evidence.upper(),
        "total_cases": len(items),
        "counts": counts,
        "items": items,
    }


def write_registry_apply_plan(
    path: str | Path,
    plan: dict[str, Any],
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(output)
    return output
