from __future__ import annotations

from monitoring.services.custom_service_index import backfill_record_index, build_record_index_payload


def test_build_record_index_payload_excludes_credentials() -> None:
    service = {
        "code": "apps",
        "label": "Applications",
        "fields": [
            {"field_key": "name", "label": "Nom", "show_in_list": True, "searchable": True},
            {"field_key": "ip", "label": "IP", "show_in_list": False, "searchable": True},
            {"field_key": "hidden", "label": "Masque", "show_in_list": False, "searchable": False},
        ],
    }
    record = {
        "id": "rec-1",
        "service_code": "apps",
        "values": {
            "name": "Portail",
            "ip": "192.0.2.10",
            "hidden": "not-indexed",
            "device_login": "admin",
            "device_password": "secret",
        },
        "children": [{"name": "Child A", "code": "child-a"}],
    }

    payload = build_record_index_payload(service=service, record=record)

    assert payload["record_id"] == "rec-1"
    assert payload["service_code"] == "apps"
    assert payload["label_value"] == "Portail"
    assert "192.0.2.10" in payload["search_blob"]
    assert "Child A" in payload["search_blob"]
    assert "not-indexed" not in payload["search_blob"]
    assert "admin" not in payload["search_blob"]
    assert "secret" not in payload["search_blob"]
    assert "device_login" not in payload["search_blob"]
    assert "device_password" not in payload["search_blob"]


class _BackfillManager:
    def __init__(self) -> None:
        self.services = [
            {
                "code": "apps",
                "label": "Applications",
                "fields": [{"field_key": "name", "label": "Nom"}],
            }
        ]
        self.records = [
            {
                "id": "rec-1",
                "service_code": "apps",
                "values": {"name": "Portail"},
                "children": [],
            },
            {
                "id": "rec-2",
                "service_code": "apps",
                "values": {"name": "Intranet"},
                "children": [],
            },
        ]
        self.index: dict[str, dict] = {}

    def list_custom_services(self) -> list[dict]:
        return self.services

    def list_custom_service_records_missing_index(self, *, limit: int = 100) -> list[dict]:
        missing = [row for row in self.records if row["id"] not in self.index]
        return missing[:limit]

    def upsert_custom_service_record_index(self, **payload) -> None:
        self.index[payload["record_id"]] = dict(payload)


def test_backfill_record_index_is_idempotent() -> None:
    manager = _BackfillManager()

    first_count = backfill_record_index(manager=manager, batch_size=1)
    second_count = backfill_record_index(manager=manager, batch_size=1)

    assert first_count == 2
    assert second_count == 0
    assert sorted(manager.index) == ["rec-1", "rec-2"]
    assert manager.index["rec-1"]["label_value"] == "Portail"
