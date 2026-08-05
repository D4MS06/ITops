from __future__ import annotations

from monitoring.services.custom_service_history import build_field_history_events
from monitoring.services.custom_service_schema import normalize_service_fields, validate_record_values
from monitoring.api.schemas import CustomServiceRecordUpsertRequest


def test_normalize_service_fields_preserves_history_flag() -> None:
    fields = normalize_service_fields(
        [
            {
                "field_key": "status",
                "label": "Status",
                "field_kind": "text",
                "track_history": True,
            }
        ]
    )

    assert fields[0]["track_history"] is True


def test_normalize_service_fields_preserves_table_behavior_flags() -> None:
    fields = normalize_service_fields(
        [
            {
                "field_key": "status",
                "label": "Status",
                "field_kind": "list",
                "options": "Actif,Inactif",
                "inline_editable": True,
                "quick_filter": True,
            }
        ]
    )

    assert fields[0]["inline_editable"] is True
    assert fields[0]["quick_filter"] is True


def test_normalize_service_fields_allows_batch_editing_only_for_lists() -> None:
    fields = normalize_service_fields(
        [
            {
                "field_key": "status",
                "label": "Statut",
                "field_kind": "list",
                "options": "En service,A jeter",
                "batch_editable": True,
            },
            {
                "field_key": "reference",
                "label": "Reference",
                "field_kind": "text",
                "batch_editable": True,
            },
        ]
    )

    assert fields[0]["batch_editable"] is True
    assert fields[1]["batch_editable"] is False


def test_build_field_history_events_only_tracks_changed_enabled_fields() -> None:
    fields = [
        {"field_key": "status", "track_history": True},
        {"field_key": "site", "track_history": False},
    ]

    events = build_field_history_events(
        fields=fields,
        old_values={"status": "OK", "site": "Paris"},
        new_values={"status": "KO", "site": "Lyon"},
    )

    assert events == [{"field_key": "status", "old_value": "OK", "new_value": "KO"}]


def test_build_field_history_events_is_idempotent_without_value_change() -> None:
    events = build_field_history_events(
        fields=[{"field_key": "status", "track_history": True}],
        old_values={"status": "OK"},
        new_values={"status": "OK"},
    )

    assert events == []


def test_record_upsert_request_supports_skipping_history_changes() -> None:
    payload = CustomServiceRecordUpsertRequest(
        values={"status": "Sortie d'inventaire"},
        skip_history_changes=True,
    )

    assert payload.confirm_history_changes is False
    assert payload.skip_history_changes is True


def test_validate_record_values_normalizes_common_date_formats() -> None:
    values = validate_record_values(
        fields=[{"field_key": "installed_at", "label": "Date d'installation", "field_kind": "date"}],
        values={"installed_at": "31/12/2025"},
        fill_defaults=False,
    )

    assert values["installed_at"] == "2025-12-31"
