from traceai_reconciliation.cli import build_parser


def test_cli_default_rules_version_matches_v04() -> None:
    args = build_parser().parse_args([])
    assert args.rules_version == "0.4"
