from contextlib import nullcontext
import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _execute_custom_service_automation_event, _register_config_routes
from monitoring.services.module_permissions import custom_service_module_code


def test_document_routes_require_module_permissions():
    grants = set()
    calls = []
    class Store:
        def subject_has_module_permission(self, *, subject, module_code, permission):
            calls.append((module_code, permission))
            return permission in grants

        def get_custom_service(self, *, code):
            return {"code": code}

        def list_linked_files(self, **kwargs):
            return []

    app = FastAPI()
    _register_config_routes(app, lambda: SimpleNamespace(logs=Store()), lambda: SimpleNamespace(subject="user"), lambda: None)
    client = TestClient(app)
    url = "/admin/custom-services/quotes/records/1/document-links"
    assert client.get(url, params={"document_field_key": "devis"}).status_code == 403
    assert client.delete(url + "/file").status_code == 403
    assert client.post(url, json={"root_id": "local", "path": "a.pdf", "document_field_key": "devis"}).status_code == 403
    grants.add("read")
    assert client.get(url, params={"document_field_key": "devis"}).status_code == 200
    assert client.delete(url + "/file").status_code == 403
    grants.add("update")
    assert client.delete(url + "/file", params={"delete_physical_file": "true"}).status_code == 403
    assert calls[-1][1] == "delete"
    assert all(code == custom_service_module_code("quotes") for code, _ in calls)


def test_document_event_fills_empty_date_and_preserves_manual_date():
    class Store:
        def save_custom_service_record(self, **kwargs):
            return {"id": kwargs["record_id"], "values": kwargs["values"]}

    service = {"code": "quotes", "automation_rules": [{"id": "receive", "trigger": {"type": "document_linked", "field_key": "devis"}, "actions": [{"type": "set_field_from_event", "field_key": "date_reception", "event_value_key": "linked_at", "only_if_empty": True}]}]}
    event = {"type": "document_linked", "field_key": "devis", "linked_at": "2026-11-23", "source": "manual"}
    api = SimpleNamespace(logs=Store())
    for initial, expected in [("", "2026-11-23"), ("2026-11-01", "2026-11-01")]:
        record = {"id": "1", "values": {"date_reception": initial}}
        result = _execute_custom_service_automation_event(api.logs, service=service, record=record, event=event)
        assert result["values"]["date_reception"] == expected
    raw_service = {"code": "quotes", "treeview_config": json.dumps({"automation_rules": service["automation_rules"]})}
    result = _execute_custom_service_automation_event(api.logs, service=raw_service, record={"id": "1", "values": {}}, event=event)
    assert result["values"]["date_reception"] == "2026-11-23"


def test_link_checks_configuration_and_dispatches_event(tmp_path):
    folder = tmp_path / "itops-records" / "quotes" / "1" / "devis"
    folder.mkdir(parents=True)
    (folder / "devis.pdf").write_bytes(b"test")
    config = {"tile": {"documents": {"enabled": True, "entries": [{"field_key": "devis", "storage_root_id": "local:linked_files"}]}}, "automation_rules": [{"id": "receive", "trigger": {"type": "document_linked", "field_key": "devis"}, "actions": [{"type": "set_field_from_event", "field_key": "received", "event_value_key": "linked_at", "only_if_empty": True}]}]}
    class Store:
        def __init__(self):
            self.record = {"id": "1", "values": {}}
            self.links = []

        def subject_has_module_permission(self, **kwargs):
            return True

        def get_custom_service(self, *, code):
            return {"code": code, "treeview_config": json.dumps(config)}

        def list_custom_service_records(self, **kwargs):
            return [self.record] if kwargs["record_id"] == self.record["id"] else []

        def list_linked_files(self, **kwargs):
            return self.links

        def get_linked_file(self, *, file_id):
            return next((row for row in self.links if row["id"] == file_id), None)

        def document_link_transaction(self, *, service_code, record_id):
            return nullcontext(self if record_id == self.record["id"] else None)

        def upsert_linked_file(self, **kwargs):
            if self.links and kwargs["create_only"]:
                return self.links[0]
            row = {**kwargs, "id": kwargs["file_id"], "created_at": "2026-11-23"}
            self.links.append(row)
            return row

        def save_custom_service_record(self, **kwargs):
            self.record = {"id": kwargs["record_id"], "values": kwargs["values"]}
            return self.record

    store = Store()
    api = SimpleNamespace(logs=store, device_config_files=SimpleNamespace(local_storage_root_dir=lambda: tmp_path), storage_targets=SimpleNamespace(list_targets=lambda **kwargs: []))
    app = FastAPI()
    _register_config_routes(app, lambda: api, lambda: SimpleNamespace(subject="user"), lambda: None)
    client = TestClient(app)
    url = "/admin/custom-services/quotes/records/1/document-links"
    payload = {"root_id": "local:linked_files", "path": "itops-records/quotes/1/devis/devis.pdf", "document_field_key": "devis"}
    assert client.post(url, json={**payload, "document_field_key": "other"}).status_code == 422
    assert client.post(url.replace("/1/", "/missing/"), json=payload).status_code == 403
    assert client.post(url, json=payload).status_code == 200
    assert store.record["values"]["received"] == "2026-11-23"
    first_link = store.links[0]["id"]
    assert client.post(url, json=payload).json()["id"] == first_link
    store.links[0]["owner_id"] = "another-record"
    assert client.post(url, json=payload).status_code == 409
    assert store.links[0]["owner_id"] == "another-record"
    store.links[0]["owner_id"] = "1"
    store.links[0]["metadata"] = {"root_id": payload["root_id"], "path": "moved.pdf"}
    assert client.delete(url + "/" + first_link, params={"delete_physical_file": True}).status_code == 409
    assert (folder / "devis.pdf").is_file()


def test_storage_upload_does_not_overwrite_existing_file(tmp_path):
    original = tmp_path / "devis.pdf"
    original.write_bytes(b"original")
    api = SimpleNamespace(device_config_files=SimpleNamespace(local_storage_root_dir=lambda: tmp_path), storage_targets=SimpleNamespace(list_targets=lambda **kwargs: []))
    app = FastAPI()
    _register_config_routes(app, lambda: api, lambda: SimpleNamespace(subject="sa"), lambda: None)
    client = TestClient(app)
    response = client.post("/storage/explorer/upload", json={"root_id": "local:linked_files", "path": "", "filename": "devis.pdf", "content_base64": "bmV3"})
    assert response.status_code == 409
    assert original.read_bytes() == b"original"


def test_explorer_limits_reader_to_the_configured_record_folder(tmp_path):
    field = "attachment"
    folder = tmp_path / "itops-records" / "quotes" / "1" / field
    folder.mkdir(parents=True)
    (folder / "sample.pdf").write_bytes(b"sample")
    grant = {"module": custom_service_module_code("quotes")}
    service = {"code": "quotes", "treeview_config": json.dumps({"tile": {"documents": {
        "enabled": True, "entries": [{"storage_root_id": "local:linked_files", "field_key": field}]
    }}})}
    logs = SimpleNamespace(
        subject_has_module_permission=lambda *, subject, module_code, permission: module_code == grant["module"] and permission == "read",
        get_custom_service=lambda *, code: service if code == "quotes" else None,
        list_custom_services=lambda: [service],
        custom_service_record_exists=lambda *, service_code, record_id: record_id == "1",
    )
    device_dir = tmp_path / "devices"
    device_dir.mkdir()
    device_target = SimpleNamespace(id="network", label="Network", kind="smb3",
                                   service_code="monitoring.device_config_files", service_label="Monitoring",
                                   local_mount_path=str(device_dir), remote_path=str(device_dir))
    api = SimpleNamespace(logs=logs, device_config_files=SimpleNamespace(local_storage_root_dir=lambda: tmp_path),
                          storage_targets=SimpleNamespace(list_targets=lambda **kw: [device_target], get_target=lambda key: device_target if key == device_target.id else None))
    app = FastAPI()
    session = lambda: SimpleNamespace(subject="reader")
    _register_config_routes(app, lambda: api, session, session)
    client = TestClient(app)
    base = "/storage/explorer/"
    params = {"root_id": "local:linked_files", "path": "itops-records/quotes/1/attachment"}
    assert [row["id"] for row in client.get(base + "roots").json()] == ["local:linked_files"]
    assert client.get(base + "list", params=params).status_code == 200
    assert client.get(base + "download", params={**params, "path": params["path"] + "/sample.pdf"}).content == b"sample"
    assert client.get(base + "list", params={**params, "path": ""}).status_code == 403
    assert client.get(base + "list", params={**params, "create_if_missing": True}).status_code == 403
    grant["module"] = "monitoring"
    assert client.get(base + "list", params=params).status_code == 403
    assert client.get(base + "list", params={"root_id": "target:network"}).status_code == 200
