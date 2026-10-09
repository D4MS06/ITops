from monitoring.repositories.device_type_schema_normalizer import normalize_type_schema_payload


def test_normalize_type_schema_payload_preserves_table_visibility():
    fields, actions, seen = normalize_type_schema_payload(
        fields=[
            {"field_key": "name", "label": "Nom", "field_kind": "text", "required": True},
            {"field_key": "ip", "label": "IP", "field_kind": "ip", "required": True, "show_in_table": False},
            {"field_key": "site", "label": "Site", "field_kind": "text", "show_in_table": True},
        ],
        actions=[],
    )

    assert actions == []
    assert seen == {"name", "ip", "site"}
    assert {field["field_key"]: field["show_in_table"] for field in fields} == {
        "name": 1,
        "ip": 0,
        "site": 1,
    }
