from __future__ import annotations

from pathlib import Path
import tomllib

from traceai_reconciliation import __version__
from traceai_reconciliation.version import (
    DAILY_RUN_SCHEMA_VERSION,
    ENGINE_VERSION,
    OPERATOR_OUTPUT_SCHEMA_VERSION,
    RULESET_VERSION,
)


def test_package_version_matches_engine_contract() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert payload["project"]["version"] == ENGINE_VERSION
    assert __version__ == ENGINE_VERSION


def test_version_contracts_are_explicit() -> None:
    assert ENGINE_VERSION == "0.10.0"
    assert RULESET_VERSION
    assert DAILY_RUN_SCHEMA_VERSION
    assert OPERATOR_OUTPUT_SCHEMA_VERSION
