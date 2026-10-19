"""TRACEAI-EXT-001: client-neutral configuration contract (no execution engine).

Does not access raw files, issue matches, or change any stock operation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


_ALLOWED = frozenset({"wms", "erp", "3pl", "excel", "other"})


@dataclass(frozen=True)
class SourceProfile:
    key: str
    kind: str
    columns: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("Source key required")
        if self.kind not in _ALLOWED:
            raise ValueError("Unsupported source type")
        if not self.columns or any(not k.strip() or not v.strip() for k, v in self.columns.items()):
            raise ValueError("Explicit non-empty column mappings required")
        if len(set(self.columns.values())) != len(self.columns):
            raise ValueError("One source column cannot map to multiple canonical fields")


@dataclass(frozen=True)
class ClientProfile:
    profile_id: str
    sources: tuple[SourceProfile, ...]
    operation_map: Mapping[str, str]
    warehouse_aliases: Mapping[str, str]
    enforce_single_warehouse_invoice: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id or not self.profile_id.strip():
            raise ValueError("Profile ID required")
        if len(self.sources) < 2 or len({s.key for s in self.sources}) != len(self.sources):
            raise ValueError("Two or more distinctly named sources required")
        if any(not k.strip() or not v.strip() for k, v in self.operation_map.items()):
            raise ValueError("Operation mappings cannot be blank")
        if any(not k.strip() or not v.strip() for k, v in self.warehouse_aliases.items()):
            raise ValueError("Warehouse aliases cannot be blank")


def validate_profile_dict(payload: Mapping[str, object]) -> ClientProfile:
    """Validate a plain mapping, rejecting unknown keys and implicit defaults."""
    allowed = {"profile_id", "sources", "operation_map",
               "warehouse_aliases", "enforce_single_warehouse_invoice"}
    if set(payload) - allowed or not {"profile_id", "sources", "operation_map", "warehouse_aliases"} <= set(payload):
        raise ValueError("Missing or unrecognized profile fields")
    raw_sources = payload["sources"]
    if not isinstance(raw_sources, list):
        raise ValueError("Sources must be a list")
    sources = []
    for src in raw_sources:
        if not isinstance(src, dict) or set(src) != {"key", "kind", "columns"} or not isinstance(src["columns"], dict):
            raise ValueError("Invalid source definition")
        if not all(isinstance(v, str) for v in [src["key"], src["kind"], *src["columns"].keys(), *src["columns"].values()]):
            raise ValueError("Source mappings must contain strings")
        sources.append(SourceProfile(**src))
    for field in ("operation_map", "warehouse_aliases"):
        obj = payload[field]
        if not isinstance(obj, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in obj.items()):
            raise ValueError(f"Invalid {field}")
    policy = payload.get("enforce_single_warehouse_invoice", False)
    if not isinstance(policy, bool):
        raise ValueError("Warehouse invoice policy must be boolean")
    if not isinstance(payload["profile_id"], str):
        raise ValueError("Invalid profile ID")
    return ClientProfile(payload["profile_id"], tuple(sources), payload["operation_map"],
                         payload["warehouse_aliases"], policy)
