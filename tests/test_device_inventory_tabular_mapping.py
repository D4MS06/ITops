from __future__ import annotations

from monitoring.services.device_inventory_tabular import infer_devices_from_rows, resolve_effective_column_mapping


def test_device_import_mapping_uses_shared_manual_resolution() -> None:
    rows, _detected_rows, _detected_columns, issues = infer_devices_from_rows(
        headers=["A", "B", "C"],
        raw_rows=[["switch", "192.0.2.10", "Core"]],
        allowed_device_types={"switch"},
        column_mappings=[
            {"source_column": "A", "target_field": "device_type"},
            {"source_column": "B", "target_field": "ip"},
            {"source_column": "C", "target_field": "name"},
        ],
    )

    assert issues == []
    assert rows[0]["device_type"] == "switch"
    assert rows[0]["ip"] == "192.0.2.10"
    assert rows[0]["name"] == "Core"


def test_device_import_effective_mapping_is_preserved() -> None:
    mapping = resolve_effective_column_mapping(
        headers=["A", "B"],
        column_mappings=[
            {"source_column": "A", "target_field": "ip"},
            {"source_column": "B", "target_field": "custom", "custom_key": "site"},
        ],
    )

    assert mapping == [
        {"source_column": "A", "target_field": "ip", "custom_key": ""},
        {"source_column": "B", "target_field": "custom", "custom_key": "site"},
    ]
