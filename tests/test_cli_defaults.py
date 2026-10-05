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



def test_cli_registry_manifest_arguments_parse() -> None:
    args = build_parser().parse_args(
        [
            "--registry-export",
            "registry.csv",
            "--manifest-output",
            "manifest.json",
            "--batch-limit",
            "10",
            "--registry-status",
            "DESCHIS",
            "--registry-status",
            "IN_ANALIZA",
            "--exclude-case-id",
            "CASE-OLD",
            "--exclude-product",
            "DS999",
        ]
    )

    assert args.registry_export == "registry.csv"
    assert args.manifest_output == "manifest.json"
    assert args.batch_limit == 10
    assert args.registry_status == ["DESCHIS", "IN_ANALIZA"]
    assert args.exclude_case_id == ["CASE-OLD"]
    assert args.exclude_product == ["DS999"]
