from __future__ import annotations

from pathlib import Path
import re
import tomllib

from traceai_reconciliation import __version__
from traceai_reconciliation.investigation.artifact_gate import (
    REQUIRED_CASE_ARTIFACTS,
)
from traceai_reconciliation.run_store.sqlite_store import SCHEMA_VERSION
from traceai_reconciliation.version import (
    DAILY_CASE_SUMMARY_SCHEMA_VERSION,
    DAILY_RUN_SCHEMA_VERSION,
    ENGINE_VERSION,
    OPERATOR_OUTPUT_SCHEMA_VERSION,
    RULESET_VERSION,
    SELF_SERVICE_BATCH_SCHEMA_VERSION,
    SELF_SERVICE_SUMMARY_SCHEMA_VERSION,
)


def test_release_engine_and_package_versions_are_synchronized() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    package_version = payload["project"]["version"]

    assert package_version == ENGINE_VERSION
    assert __version__ == ENGINE_VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+", ENGINE_VERSION)


def test_release_contract_versions_are_explicit() -> None:
    contracts = {
        "ruleset": RULESET_VERSION,
        "daily_run": DAILY_RUN_SCHEMA_VERSION,
        "operator_output": OPERATOR_OUTPUT_SCHEMA_VERSION,
        "daily_case_summary": DAILY_CASE_SUMMARY_SCHEMA_VERSION,
        "self_service_summary": SELF_SERVICE_SUMMARY_SCHEMA_VERSION,
        "self_service_batch": SELF_SERVICE_BATCH_SCHEMA_VERSION,
    }

    assert all(str(value).strip() for value in contracts.values())


def test_release_requires_current_run_store_schema() -> None:
    assert SCHEMA_VERSION >= 3


def test_release_requires_complete_operator_artifact_set() -> None:
    assert REQUIRED_CASE_ARTIFACTS == (
        "case.json",
        "case.docx",
        "registry_update.json",
        "review_queue.json",
        "self_service_summary.json",
        "daily_operator_result.json",
        "daily_case_summary.json",
    )


def test_release_readiness_document_exists() -> None:
    path = Path("docs/RELEASE_READINESS_V0_12.md")

    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    for required in (
        "Freeze funcțional",
        "Golden Gate",
        "snapshot_at",
        "automatic approval disabled",
        "WMS mutation disabled",
        "WME mutation disabled",
    ):
        assert required in content
