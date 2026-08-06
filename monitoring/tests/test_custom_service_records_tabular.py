from __future__ import annotations

from monitoring.services.custom_service_records_tabular import (
    infer_custom_service_records_from_file,
    infer_custom_service_records_from_rows,
    resolve_effective_record_column_mapping,
)


def test_infer_custom_service_records_imports_credentials_when_enabled():
    payload = "record_id,Nom,device_login,device_password\n42,Imprimante A,admin,secret\n".encode("utf-8")
    rows, detected_rows, detected_columns, issues = infer_custom_service_records_from_file(
        filename="records.csv", content_bytes=payload,
        fields=[{"field_key": "name", "label": "Nom", "field_kind": "text", "required": False}],
        credentials_enabled=True,
    )
    assert (detected_rows, detected_columns, issues) == (1, 4, [])
    assert rows[0]["values"]["device_login"] == "admin"
    assert rows[0]["values"]["device_password"] == "secret"


def test_infer_custom_service_records_does_not_import_credentials_when_disabled():
    payload = "record_id,Nom,device_login,device_password\n42,Imprimante A,admin,secret\n".encode("utf-8")
    rows, *_rest = infer_custom_service_records_from_file(
        filename="records.csv", content_bytes=payload,
        fields=[{"field_key": "name", "label": "Nom", "field_kind": "text", "required": False}],
    )
    assert "device_login" not in rows[0]["values"]
    assert "device_password" not in rows[0]["values"]


def test_infer_custom_service_records_omits_unmapped_fields():
    payload = "Service,Status\nSports,En service\n".encode("utf-8")
    rows, *_rest = infer_custom_service_records_from_file(
        filename="records.csv", content_bytes=payload,
        fields=[{"field_key": "service", "label": "Service"}, {"field_key": "status", "label": "Status"}],
        column_mappings=[{"source_column": "Service", "target_field": "service"}, {"source_column": "Status", "target_field": "__ignore__"}],
    )
    assert rows[0]["values"] == {"service": "Sports"}


def test_infer_custom_service_records_maps_custom_credential_headers_when_enabled():
    payload = "Adresse,Secret du coffre\nsupport@example.test,secret\n".encode("utf-8")
    mappings = [{"source_column": "Adresse", "target_field": "address"}, {"source_column": "Secret du coffre", "target_field": "device_password"}]
    rows, *_rest = infer_custom_service_records_from_file(
        filename="emails.csv", content_bytes=payload,
        fields=[{"field_key": "address", "label": "Adresse", "field_kind": "text", "required": True}],
        column_mappings=mappings, credentials_enabled=True,
    )
    assert rows[0]["values"] == {"address": "support@example.test", "device_password": "secret"}
    assert resolve_effective_record_column_mapping(headers=["Adresse", "Secret du coffre"], fields=[{"field_key": "address", "label": "Adresse"}], column_mappings=mappings, credentials_enabled=True)[1]["target_field"] == "device_password"


def test_record_import_falls_back_to_positional_mapping_when_headers_do_not_match():
    rows, detected_rows, detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["Colonne A", "Colonne B"], rows=[["Portail", "192.0.2.10"]],
        fields=[{"field_key": "name", "label": "Nom"}, {"field_key": "ip", "label": "IP"}],
    )
    assert (detected_rows, detected_columns) == (1, 2)
    assert issues == ["Aucune correspondance exacte d'entete: colonnes mappees par position."]
    assert rows[0]["values"] == {"name": "Portail", "ip": "192.0.2.10"}


def test_record_import_uses_positional_mapping_for_remaining_unmatched_fields():
    rows, _detected_rows, _detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["record_id", "Nom", "Colonne B", "Colonne C", "Colonne D"],
        rows=[["rec-1", "Portail", "192.0.2.10", "https://example.test", "ignore-me"]],
        fields=[{"field_key": "name", "label": "Nom"}, {"field_key": "ip", "label": "IP"}, {"field_key": "url", "label": "URL"}],
    )
    assert issues == ["Certaines colonnes sans correspondance exacte ont ete mappees par position."]
    assert rows[0]["record_id"] == "rec-1"
    assert rows[0]["values"] == {"name": "Portail", "ip": "192.0.2.10", "url": "https://example.test"}


def test_record_import_uses_manual_column_mapping():
    rows, _detected_rows, _detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["A", "B", "C"], rows=[["value-a", "value-b", "value-c"]],
        fields=[{"field_key": "x", "label": "X"}, {"field_key": "y", "label": "Y"}],
        column_mappings=[{"source_column": "C", "target_field": "x"}, {"source_column": "A", "target_field": "y"}],
    )
    assert "Mapping manuel applique." in issues
    assert rows[0]["values"] == {"x": "value-c", "y": "value-a"}


def test_import_rows_keep_source_values_for_history_date_mapping() -> None:
    rows, _count, _columns, _issues = infer_custom_service_records_from_rows(
        headers=["Etat", "Date de changement"],
        rows=[["En service", "14/08/2026"]],
        fields=[
            {
                "field_key": "etat",
                "label": "Etat",
                "field_kind": "list",
                "options": "En service,Hors service",
                "track_history": True,
            }
        ],
        include_source_values=True,
    )

    assert rows[0]["values"] == {"etat": "En service"}
    assert rows[0]["source_values"]["Date de changement"] == "14/08/2026"
