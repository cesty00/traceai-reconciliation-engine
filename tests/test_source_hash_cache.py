from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from traceai_reconciliation.investigation.source_hash_cache import (
    SourceHashCache,
    hash_sources,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_source_hash_cache_reuses_metadata_and_invalidates_on_change(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    cache_dir = tmp_path / "cache"

    first_bytes = b"a;b\n1;2\n"
    source.write_bytes(first_bytes)

    first = hash_sources(
        {"wms": source},
        cache_dir=cache_dir,
    )
    assert first["wms"] == _sha256(first_bytes)

    cache_file = cache_dir / "source_hashes.json"
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    key = str(source.resolve())
    assert payload["entries"][key]["sha256"] == first["wms"]

    second = hash_sources(
        {"wms": source},
        cache_dir=cache_dir,
    )
    assert second == first

    second_bytes = b"a;b\n1;3\n"
    source.write_bytes(second_bytes)
    stat = source.stat()
    os.utime(
        source,
        ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000),
    )

    third = hash_sources(
        {"wms": source},
        cache_dir=cache_dir,
    )
    assert third["wms"] == _sha256(second_bytes)
    assert third["wms"] != first["wms"]


def test_corrupt_hash_cache_is_rebuilt(tmp_path: Path) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"test-bytes")
    cache_file = tmp_path / "cache" / "source_hashes.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("{broken", encoding="utf-8")

    cache = SourceHashCache(cache_file)
    digest = cache.hash_file(source)

    assert digest == _sha256(b"test-bytes")
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
