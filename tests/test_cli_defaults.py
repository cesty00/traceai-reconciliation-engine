from traceai_reconciliation.cli import build_parser


def test_cli_default_rules_version_matches_v04() -> None:
    args = build_parser().parse_args([])
    assert args.rules_version == "0.4"



def test_cli_batch_arguments_parse() -> None:
    args = build_parser().parse_args(
        [
            "--batch-manifest",
            "manifest.json",
            "--batch-output-dir",
            "out",
            "--batch-id",
            "BATCH-001",
            "--no-reuse-completed",
        ]
    )

    assert args.batch_manifest == "manifest.json"
    assert args.batch_output_dir == "out"
    assert args.batch_id == "BATCH-001"
    assert args.no_reuse_completed is True
    assert args.rules_version == "0.4"
