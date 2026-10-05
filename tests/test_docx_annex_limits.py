from traceai_reconciliation.reports.docx_report import (
    _sample_rows_for_docx,
)


def test_docx_annex_sampling_keeps_head_and_tail() -> None:
    rows = [(index,) for index in range(1000)]

    selected, omitted = _sample_rows_for_docx(rows, limit=500)

    assert len(selected) == 500
    assert omitted == 500
    assert selected[0] == (0,)
    assert selected[249] == (249,)
    assert selected[250] == (750,)
    assert selected[-1] == (999,)


def test_docx_annex_sampling_keeps_small_tables_complete() -> None:
    rows = [(1,), (2,), (3,)]

    selected, omitted = _sample_rows_for_docx(rows, limit=500)

    assert selected == rows
    assert omitted == 0
