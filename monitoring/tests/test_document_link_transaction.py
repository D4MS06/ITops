"""Opt-in MariaDB regression test using connection-local temporary tables."""
from contextlib import nullcontext
import json
import os
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from monitoring.api.app import _register_config_routes
from monitoring.storage.mariadb_manager import MariaDBFileManager


@pytest.mark.skipif(os.getenv("ITOPS_TEST_MARIADB") != "1", reason="requires the ITops MariaDB schema")
def test_document_link_rolls_back_and_can_be_retried(monkeypatch, tmp_path):
    manager = MariaDBFileManager()
    tables = ("custom_service_records", "custom_service_children", "custom_service_record_history",
              "custom_service_record_index", "linked_files", "app_settings")
    root = "local:linked_files"
    rule = {"trigger": {"type": "document_linked", "field_key": "quote"},
            "actions": [{"type": "set_field_from_event", "field_key": "received"}]}
    config = {"tile": {"documents": {"enabled": True, "entries": [
        {"field_key": "quote", "storage_root_id": root}]}}, "automation_rules": [rule],
        "validation_rules": [{"condition": {"field_key": "received", "operator": "not_empty"},
                              "required_field_keys": ["sent"], "message": "Envoyez la demande avant réception."}]}
    service = {"code": "audit", "treeview_config": json.dumps(config),
               "fields": [{"field_key": "received", "field_kind": "date", "track_history": True}]}
    with manager._connect() as connection:
        with connection.cursor() as cursor:
            for table in tables:
                if table == "custom_service_record_index":
                    # InnoDB temporary tables support the unique key but not the full-text index.
                    cursor.execute("CREATE TEMPORARY TABLE test_schema_custom_service_record_index "
                                   "ENGINE=InnoDB AS SELECT * FROM custom_service_record_index LIMIT 0")
                    cursor.execute("ALTER TABLE test_schema_custom_service_record_index ADD PRIMARY KEY(record_id)")
                    cursor.execute("CREATE TEMPORARY TABLE custom_service_record_index LIKE test_schema_custom_service_record_index")
                    continue
                cursor.execute(f"CREATE TEMPORARY TABLE test_schema_{table} LIKE {table}")
                cursor.execute(f"CREATE TEMPORARY TABLE {table} LIKE test_schema_{table}")
        # Every operation, including verification after rollback, sees only these temporary tables.
        monkeypatch.setattr(manager, "_open_connection", lambda: nullcontext(connection))
        monkeypatch.setattr(manager, "_bootstrap_completed", True)
        monkeypatch.setattr(manager, "get_custom_service", lambda **_: service)
        monkeypatch.setattr(manager, "list_custom_service_relations", lambda **_: [])
        manager.save_custom_service_record(service_code="audit", record_id="one", values={}, children=[])
        (tmp_path / "quote.pdf").write_bytes(b"test document")
        api = SimpleNamespace(logs=manager, device_config_files=SimpleNamespace(local_storage_root_dir=lambda: tmp_path))
        app = FastAPI()
        session = lambda: SimpleNamespace(subject="sa")
        _register_config_routes(app, lambda: api, session, session)
        client = TestClient(app, raise_server_exceptions=False)
        url = "/admin/custom-services/audit/records/one/document-links"
        body = {"root_id": root, "path": "quote.pdf", "document_field_key": "quote"}

        def date_value():
            record, = manager.list_custom_service_records(service_code="audit", record_id="one")
            return record["values"].get("received")

        blocked = client.post(url, json=body)
        assert blocked.status_code == 422
        assert blocked.json()["detail"] == "Envoyez la demande avant réception."
        assert manager.get_linked_file_by_stored_path(stored_path=str(tmp_path / "quote.pdf")) is None
        assert not date_value()
        manager.save_custom_service_record(service_code="audit", record_id="one",
                                          values={"sent": "2026-11-01"}, children=[])

        for method in ("save_custom_service_record", "save_automation_execution_log"):
            original = getattr(MariaDBFileManager, method)
            completed_writes = []

            def fail_after_write(self, **kwargs):
                original(self, **kwargs)
                completed_writes.append(method)
                raise RuntimeError("Injected database failure")

            with monkeypatch.context() as patch:
                patch.setattr(MariaDBFileManager, method, fail_after_write)
                assert client.post(url, json=body).status_code == 500
            assert completed_writes == [method]
            assert manager.get_linked_file_by_stored_path(stored_path=str(tmp_path / "quote.pdf")) is None
            assert not date_value()
            assert not manager.list_automation_execution_logs(service_code="audit")
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM custom_service_record_history")
                assert cursor.fetchone()[0] == 0

        saved = client.post(url, json=body)
        assert saved.status_code == 200
        assert date_value() == saved.json()["created_at"][:10]
        assert client.post(url, json=body).json()["id"] == saved.json()["id"]
        assert len(manager.list_automation_execution_logs(service_code="audit")) == 1
