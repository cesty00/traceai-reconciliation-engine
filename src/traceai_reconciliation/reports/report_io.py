from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .report_model import CaseReport, Recommendation


def case_report_from_dict(data: dict[str, Any]) -> CaseReport:
    payload = dict(data)
    payload["recommendations"] = [
        item if isinstance(item, Recommendation) else Recommendation(**item)
        for item in payload.get("recommendations", [])
    ]
    return CaseReport(**payload)


def load_case_report_json(path: str | Path) -> CaseReport:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Case report JSON must contain one object.")
    return case_report_from_dict(data)
