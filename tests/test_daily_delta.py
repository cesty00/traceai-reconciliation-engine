from __future__ import annotations

from traceai_reconciliation.investigation.daily_delta import (
    classify_snapshot_delta,
)


def test_delta_classifies_new_changed_and_unchanged() -> None:
    current = {
        "CASE-NEW": {
            "product_code": "NEW",
            "difference_reported": 3.0,
        },
        "CASE-CHANGED": {
            "product_code": "CHANGED",
            "difference_reported": -2.0,
        },
        "CASE-SAME": {
            "product_code": "SAME",
            "difference_reported": 1.5,
        },
    }
    previous = {
        "CASE-CHANGED": {
            "product_code": "CHANGED",
            "difference_reported": -1.0,
        },
        "CASE-SAME": {
            "product_code": "SAME",
            "difference_reported": 1.5,
        },
    }

    delta = classify_snapshot_delta(
        current_state=current,
        previous_state=previous,
        source_hashes_changed=True,
        previous_run_id="RUN-1",
    )

    statuses = {item.case_id: item.status for item in delta.items}
    policies = {
        item.case_id: item.execution_policy
        for item in delta.items
    }

    assert delta.new == 1
    assert delta.changed == 1
    assert delta.unchanged == 1
    assert statuses == {
        "CASE-NEW": "NEW",
        "CASE-CHANGED": "CHANGED",
        "CASE-SAME": "UNCHANGED",
    }
    assert policies["CASE-NEW"] == "ANALYZE"
    assert policies["CASE-CHANGED"] == "ANALYZE"
    assert policies["CASE-SAME"] == "REANALYZE_SOURCE_CHANGED"


def test_unchanged_can_be_reused_only_when_sources_unchanged() -> None:
    current = {
        "CASE-SAME": {
            "product_code": "SAME",
            "difference_reported": 1.5,
        }
    }
    previous = {
        "CASE-SAME": {
            "product_code": "SAME",
            "difference_reported": 1.5,
        }
    }

    delta = classify_snapshot_delta(
        current_state=current,
        previous_state=previous,
        source_hashes_changed=False,
        previous_run_id="RUN-1",
    )

    assert delta.unchanged == 1
    assert delta.items[0].execution_policy == "REUSE_SAFE"
