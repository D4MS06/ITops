from monitoring.services.device_inventory_tabular import infer_devices_from_rows


def test_device_import_maps_credentials_and_normalizes_custom_keys():
    rows, detected_rows, detected_columns, issues = infer_devices_from_rows(
        headers=["Site", "Adresse IP", "Utilisateur", "MDP", "Nombre de ports", "VLAN"],
        raw_rows=[
            ["APIC", "192.168.0.21", "admin", "secret", "7", "10"],
        ],
        default_device_type="switch",
        allowed_device_types={"switch"},
        column_mappings=[
            {"source_column": "Site", "target_field": "custom", "custom_key": "Site"},
            {"source_column": "Adresse IP", "target_field": "ip", "custom_key": ""},
            {"source_column": "Utilisateur", "target_field": "device_login", "custom_key": ""},
            {"source_column": "MDP", "target_field": "device_password", "custom_key": ""},
            {"source_column": "Nombre de ports", "target_field": "custom", "custom_key": "Nombre de ports"},
            {"source_column": "VLAN", "target_field": "custom", "custom_key": "VLAN"},
        ],
    )

    assert detected_rows == 1
    assert detected_columns == 6
    assert issues == []
    assert rows[0]["device_login"] == "admin"
    assert rows[0]["device_password"] == "secret"
    assert rows[0]["custom_data"] == {
        "site": "APIC",
        "nombre_de_ports": "7",
        "vlan": "10",
    }
