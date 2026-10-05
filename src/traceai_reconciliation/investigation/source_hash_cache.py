from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .source_readers import sha256_file


class SourceHashCache:
    """Persistent SHA-256 cache keyed by immutable file metadata."""

    def __init__(self, cache_file: str | Path) -> None:
        self.cache_file = Path(cache_file)
        self._entries: dict[str, dict[str, int | str]] = {}
        self._load()

    def _load(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(payload, dict):
            entries = payload.get("entries", {})
            if isinstance(entries, dict):
                self._entries = entries

    def _save(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "entries": self._entries,
        }
        temporary = self.cache_file.with_suffix(
            self.cache_file.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.cache_file)

    @staticmethod
    def _metadata(path: Path) -> tuple[int, int]:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns

    def hash_file(self, path: str | Path) -> str:
        source = Path(path).resolve()
        size, mtime_ns = self._metadata(source)
        key = str(source)

        cached = self._entries.get(key)
        if (
            cached
            and cached.get("size") == size
            and cached.get("mtime_ns") == mtime_ns
            and isinstance(cached.get("sha256"), str)
        ):
            return str(cached["sha256"])

        digest = sha256_file(source)
        self._entries[key] = {
            "size": size,
            "mtime_ns": mtime_ns,
            "sha256": digest,
        }
        self._save()
        return digest

    def hash_sources(
        self,
        sources: Mapping[str, str | Path],
    ) -> dict[str, str]:
        return {
            key: self.hash_file(path)
            for key, path in sources.items()
        }


def hash_sources(
    sources: Mapping[str, str | Path],
    cache_dir: str | Path | None = None,
) -> dict[str, str]:
    """
    Hash source files with optional persistent metadata-aware caching.

    When cache_dir is omitted, behavior remains fully uncached.
    """
    if cache_dir is None:
        return {
            key: sha256_file(path)
            for key, path in sources.items()
        }

    cache = SourceHashCache(
        Path(cache_dir) / "source_hashes.json"
    )
    return cache.hash_sources(sources)
