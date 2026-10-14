"""Conservative auto-detection of official export files in a local folder."""
from __future__ import annotations

from pathlib import Path
import re

SOURCE_HINTS = {
    "stock_report": (r"raport.?stoc.?wms.?wme", r"stocuri.?cu.?diferente"),
    "opening_stock_wms": (r"stoc.?initial.?wms",),
    "wms_movements": (r"trasabilitate", r"raw.?wms"),
    "wme_ledger": (r"fisa.?magazie",),
    "production": (r"rapoarte.?productie", r"raport.?productie"),
    "nomenclature": (r"nomenclator", r"mapare.?wme.?wms"),
}
EXTENSIONS = {".csv", ".xlsx", ".xls"}


def discover_source_files(folder: str | Path) -> tuple[dict[str, Path], dict[str, list[Path]]]:
    """Never guess between ambiguous matches; return conflicts for human review."""
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError("Folderul nu există sau nu este accesibil.")
    candidates: dict[str, list[Path]] = {key: [] for key in SOURCE_HINTS}
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS or path.name.startswith("~$"):
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", path.stem.lower())
        norm = " ".join(norm.split())
        for kind, hints in SOURCE_HINTS.items():
            if any(re.search(hint, norm) for hint in hints):
                candidates[kind].append(path)
    found = {key: matches[0] for key, matches in candidates.items() if len(matches) == 1}
    problems = {key: matches for key, matches in candidates.items() if len(matches) != 1}
    if len(set(found.values())) != len(found):
        raise ValueError("Același fișier a fost clasificat ca două surse. Corectează manual.")
    return found, problems
