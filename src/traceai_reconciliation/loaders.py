from __future__ import annotations

from pathlib import Path
import pandas as pd


def read_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read a CSV/XLS/XLSX source without mutating the source file."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, **kwargs)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, **kwargs)

    raise ValueError(f"Unsupported source format: {path.suffix}")


def require_columns(df: pd.DataFrame, required: set[str], source_name: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source_name}: missing required columns: {missing}")
