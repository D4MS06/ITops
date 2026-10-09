from __future__ import annotations

from monitoring.services.tabular_mapping import (
    MappingTarget,
    normalize_column_mappings,
    resolve_tabular_column_mapping,
)


def test_normalize_column_mappings_preserves_auto_and_custom_key() -> None:
    assert normalize_column_mappings(
        [
            {"source_column": " A ", "target_field": "", "custom_key": " site "},
            {"source_column": "", "target_field": "name"},
        ]
    ) == [{"source_column": "A", "target_field": "__auto__", "custom_key": "site", "field_kind": ""}]


def test_resolve_tabular_column_mapping_applies_manual_then_auto() -> None:
    resolved = resolve_tabular_column_mapping(
        headers=["Nom", "Colonne A", ""],
        column_mappings=[{"source_column": "Colonne A", "target_field": "ip"}],
        auto_resolver=lambda header, _index: MappingTarget("known", "name" if header == "Nom" else "custom"),
        manual_resolver=lambda target, _custom: MappingTarget("known", target),
    )

    assert resolved[0] == MappingTarget("known", "name")
    assert resolved[1] == MappingTarget("known", "ip")
    assert resolved[2] == MappingTarget("ignore", "")
