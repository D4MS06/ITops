from __future__ import annotations

from monitoring.services.custom_service_records_tabular import (
    infer_custom_service_records_from_rows,
    resolve_effective_record_column_mapping,
)


def test_record_import_falls_back_to_positional_mapping_when_headers_do_not_match() -> None:
    rows, detected_rows, detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["Colonne A", "Colonne B"],
        rows=[["Portail", "192.0.2.10"]],
        fields=[
            {"field_key": "name", "label": "Nom"},
            {"field_key": "ip", "label": "IP"},
        ],
    )

    assert detected_rows == 1
    assert detected_columns == 2
    assert issues == ["Aucune correspondance exacte d'entete: colonnes mappees par position."]
    assert rows == [
            {
                "record_id": "",
                "values": {"name": "Portail", "ip": "192.0.2.10"},
                "children": [],
                "_row_index": 2,
            }
        ]


def test_record_import_uses_positional_mapping_for_remaining_unmatched_fields() -> None:
    rows, _detected_rows, _detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["record_id", "Nom", "Colonne B", "Colonne C", "Colonne D"],
        rows=[["rec-1", "Portail", "192.0.2.10", "https://example.test", "ignore-me"]],
        fields=[
            {"field_key": "name", "label": "Nom"},
            {"field_key": "ip", "label": "IP"},
            {"field_key": "url", "label": "URL"},
        ],
    )

    assert issues == ["Certaines colonnes sans correspondance exacte ont ete mappees par position."]
    assert rows == [
        {
            "record_id": "rec-1",
            "values": {
                "name": "Portail",
                "ip": "192.0.2.10",
                "url": "https://example.test",
                },
                "children": [],
                "_row_index": 2,
            }
        ]


def test_record_import_uses_manual_column_mapping() -> None:
    rows, _detected_rows, _detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["A", "B", "C"],
        rows=[["value-a", "value-b", "value-c"]],
        fields=[
            {"field_key": "x", "label": "X"},
            {"field_key": "y", "label": "Y"},
        ],
        column_mappings=[
            {"source_column": "C", "target_field": "x"},
            {"source_column": "A", "target_field": "y"},
        ],
    )

    assert "Mapping manuel applique." in issues
    assert rows == [
        {
                "record_id": "",
                "values": {"x": "value-c", "y": "value-a"},
                "children": [],
                "_row_index": 2,
            }
        ]


def test_record_import_effective_mapping_uses_shared_resolution() -> None:
    mapping = resolve_effective_record_column_mapping(
        headers=["A", "B", "C"],
        fields=[
            {"field_key": "x", "label": "X"},
            {"field_key": "y", "label": "Y"},
        ],
        column_mappings=[
            {"source_column": "C", "target_field": "x"},
            {"source_column": "A", "target_field": "y"},
        ],
    )

    assert mapping == [
        {"source_column": "A", "target_field": "y", "custom_key": ""},
        {"source_column": "B", "target_field": "__ignore__", "custom_key": ""},
        {"source_column": "C", "target_field": "x", "custom_key": ""},
    ]


def test_record_import_error_names_expected_and_detected_headers() -> None:
    try:
        infer_custom_service_records_from_rows(
            headers=["record_id"],
            rows=[[""]],
            fields=[{"field_key": "name", "label": "Nom"}],
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert "Aucune colonne du fichier ne correspond aux champs du service" in message
    assert "Champs attendus: Nom" in message
    assert "Entetes detectees: record_id" in message
