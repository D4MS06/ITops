from monitoring.services.custom_service_records_tabular import infer_custom_service_records_from_file


def test_infer_custom_service_records_imports_credentials_when_enabled():
    payload = (
        "record_id,Nom,device_login,device_password\n"
        "42,Imprimante A,admin,secret\n"
    ).encode("utf-8")
    rows, detected_rows, detected_columns, issues = infer_custom_service_records_from_file(
        filename="records.csv",
        content_bytes=payload,
        fields=[{"field_key": "name", "label": "Nom", "field_kind": "text", "required": False}],
        child_enabled=False,
        credentials_enabled=True,
    )
    assert detected_rows == 1
    assert detected_columns == 4
    assert issues == []
    assert len(rows) == 1
    assert rows[0]["_row_index"] == 2
    values = dict(rows[0].get("values") or {})
    assert values["device_login"] == "admin"
    assert values["device_password"] == "secret"


def test_infer_custom_service_records_does_not_import_credentials_when_disabled():
    payload = (
        "record_id,Nom,device_login,device_password\n"
        "42,Imprimante A,admin,secret\n"
    ).encode("utf-8")
    rows, _detected_rows, _detected_columns, _issues = infer_custom_service_records_from_file(
        filename="records.csv",
        content_bytes=payload,
        fields=[{"field_key": "name", "label": "Nom", "field_kind": "text", "required": False}],
        child_enabled=False,
        credentials_enabled=False,
    )
    values = dict(rows[0].get("values") or {})
    assert "device_login" not in values
    assert "device_password" not in values


def test_infer_custom_service_records_omits_unmapped_fields():
    payload = (
        "Service,Status\n"
        "Sports,En service\n"
    ).encode("utf-8")
    rows, _detected_rows, _detected_columns, _issues = infer_custom_service_records_from_file(
        filename="records.csv",
        content_bytes=payload,
        fields=[
            {"field_key": "service", "label": "Service", "field_kind": "text", "required": False},
            {"field_key": "status", "label": "Status", "field_kind": "text", "required": False},
        ],
        column_mappings=[
            {"source_column": "Service", "target_field": "service"},
            {"source_column": "Status", "target_field": "__ignore__"},
        ],
        child_enabled=False,
        credentials_enabled=False,
    )

    assert rows[0]["values"] == {"service": "Sports"}
