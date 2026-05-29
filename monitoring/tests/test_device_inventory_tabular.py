from monitoring.services.device_inventory_tabular import infer_devices_from_rows, resolve_effective_column_mapping


def test_manual_mapping_teamviewer_remains_known_field():
    headers = ["Type", "Nom", "IP", "TV"]
    mapping = resolve_effective_column_mapping(
        headers=headers,
        column_mappings=[
            {"source_column": "TV", "target_field": "id_Teamviewer", "custom_key": ""},
        ],
    )
    by_source = {str(row.get("source_column") or ""): row for row in mapping}
    assert by_source["TV"]["target_field"] == "id_Teamviewer"


def test_infer_devices_from_rows_uses_manual_teamviewer_mapping():
    headers = ["Type", "Nom", "IP", "TV"]
    rows = [["switch", "SW-Core", "10.0.0.10", "123456789"]]
    parsed_rows, detected_rows, detected_columns, issues = infer_devices_from_rows(
        headers=headers,
        raw_rows=rows,
        allowed_device_types={"switch"},
        column_mappings=[
            {"source_column": "TV", "target_field": "id_Teamviewer", "custom_key": ""},
        ],
    )
    assert detected_rows == 1
    assert detected_columns == 4
    assert issues == []
    assert len(parsed_rows) == 1
    assert parsed_rows[0]["id_Teamviewer"] == "123456789"
