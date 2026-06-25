from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from monitoring.services.tabular_io import normalize_cell, normalize_header_key


IGNORE_TARGETS = frozenset({"ignore", "__ignore__", "none"})
AUTO_TARGETS = frozenset({"auto", "__auto__"})


@dataclass(frozen=True, slots=True)
class MappingTarget:
    kind: str
    key: str = ""


def normalize_column_mappings(column_mappings: list[dict] | None) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in list(column_mappings or []):
        source_column = normalize_cell((row or {}).get("source_column"))
        target_field = normalize_cell((row or {}).get("target_field"))
        custom_key = normalize_cell((row or {}).get("custom_key"))
        field_kind = normalize_cell((row or {}).get("field_kind")).lower()
        if not source_column:
            continue
        output.append(
            {
                "source_column": source_column,
                "target_field": target_field or "__auto__",
                "custom_key": custom_key,
                "field_kind": field_kind,
            }
        )
    return output


def normalize_manual_column_mapping(
    column_mappings: list[dict] | None,
    *,
    resolve_target: Callable[[str, str], MappingTarget | None],
) -> dict[str, MappingTarget]:
    output: dict[str, MappingTarget] = {}
    for row in normalize_column_mappings(column_mappings):
        source_column = row["source_column"]
        target_field_raw = row["target_field"]
        target_field_token = normalize_header_key(target_field_raw)
        if not target_field_token or target_field_token in AUTO_TARGETS:
            continue
        if target_field_token in IGNORE_TARGETS:
            output[source_column] = MappingTarget("ignore", "")
            continue
        resolved = resolve_target(target_field_raw, row["custom_key"])
        if resolved is not None:
            output[source_column] = resolved
    return output


def resolve_tabular_column_mapping(
    *,
    headers: list[str],
    column_mappings: list[dict] | None = None,
    auto_resolver: Callable[[str, int], MappingTarget],
    manual_resolver: Callable[[str, str], MappingTarget | None],
) -> dict[int, MappingTarget]:
    manual_by_header = normalize_manual_column_mapping(
        column_mappings,
        resolve_target=manual_resolver,
    )
    resolved: dict[int, MappingTarget] = {}
    for index, header in enumerate(list(headers or [])):
        source_column = str(header or "")
        manual = manual_by_header.get(source_column)
        if manual is not None:
            resolved[index] = manual
            continue
        normalized = normalize_header_key(source_column)
        if not normalized:
            resolved[index] = MappingTarget("ignore", "")
            continue
        resolved[index] = auto_resolver(source_column, index)
    return resolved
