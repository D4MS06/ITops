from contextlib import nullcontext
import importlib
import json
import os
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from monitoring.api.app import _register_admin_routes
from monitoring.services.module_permissions import custom_service_module_code
from monitoring.storage.mariadb_manager import MariaDBFileManager


def test_mail_validation_failure_prevents_approval_and_smtp(monkeypatch):
    service = {
        "code": "quotes",
        "automation_rules": [{"trigger": {"type": "mail_sent"}, "actions": [
            {"type": "set_field", "field_key": "statut", "value": "Envoyé"},
        ]}],
        "validation_rules": [{"condition": {"field_key": "statut", "value": "Envoyé", "operator": "equals"},
                              "required_field_keys": ["fournisseur"], "message": "Fournisseur requis."}],
    }
    service["treeview_config"] = json.dumps({
        "automation_rules": service["automation_rules"], "validation_rules": service["validation_rules"],
    })
    draft = {"status": "awaiting_approval", "target_value": "template", "original_values": {}, "events": [{}]}
    writes, deliveries = [], []
    store = SimpleNamespace(
        subject_has_module_permission=lambda **kwargs: True,
        record_mail_id=lambda *args: "mail",
        get_provider_request=lambda **kwargs: draft,
        get_notification_template=lambda **kwargs: {
            "is_active": True, "module_code": "quotes", "task_type": "record:preview",
        },
        get_custom_service=lambda **kwargs: service,
        record_automation_transaction=lambda **kwargs: nullcontext(store),
        list_custom_service_records=lambda **kwargs: [{"id": "r", "values": {}}],
        change_record_mail=lambda **kwargs: writes.append(kwargs),
    )
    monkeypatch.setattr(importlib.import_module("monitoring.api.app"), "send_alert_email",
                        lambda *args, **kwargs: deliveries.append(args))
    app = FastAPI()
    api = SimpleNamespace(logs=store, settings_service=SimpleNamespace(get=lambda: SimpleNamespace(smtp_host="test.invalid")))
    _register_admin_routes(app, lambda: api, lambda: SimpleNamespace(subject="editor"))
    response = TestClient(app).post("/admin/custom-services/quotes/records/r/mail/approve",
        json={"revision": 1, "recipient": "test@example.org", "subject": "Sujet", "body": "Texte"})
    assert response.status_code == 422
    assert response.json()["detail"] == "Fournisseur requis."
    assert not writes and not deliveries


@pytest.mark.skipif(os.getenv("ITOPS_TEST_MARIADB") != "1", reason="requires the ITops MariaDB schema")
@pytest.mark.parametrize("failure", [None, "smtp", "confirmation"])
def test_approved_record_mail(monkeypatch, failure):
    manager = MariaDBFileManager()
    allowed = {"read", "update"}
    deliveries = []

    def deliver(subject, body, *, recipients, **kwargs):
        deliveries.append((subject, body, recipients))
        if failure == "smtp":
            raise OSError("Simulated SMTP failure")

    with manager._connect() as conn:
        with conn.cursor() as cur:
            for table in ("custom_service_records", "provider_requests", "notification_templates"):
                cur.execute(f"CREATE TEMPORARY TABLE empty_{table} LIKE {table}")
                cur.execute(f"CREATE TEMPORARY TABLE {table} LIKE empty_{table}")
            cur.execute("""INSERT INTO custom_service_records(id,service_code,payload_json,trash_reason,created_at,updated_at)
                        VALUES ('r','quotes','{}','',NOW(),NOW())""")
        conn.commit()
        monkeypatch.setattr(manager, "_open_connection", lambda: nullcontext(conn))
        monkeypatch.setattr(manager, "_bootstrap_completed", True)
        if failure == "confirmation":
            change_mail = manager.change_record_mail

            def fail_confirmation(**kwargs):
                if kwargs["action"] == "delivered":
                    raise OSError("Confirmation inaccessible")
                return change_mail(**kwargs)

            monkeypatch.setattr(manager, "change_record_mail", fail_confirmation)
        denied_modules = set()
        monkeypatch.setattr(manager, "subject_has_module_permission",
                            lambda **kw: kw["permission"] in allowed and kw["module_code"] not in denied_modules)
        monkeypatch.setattr(manager, "get_custom_service", lambda **kw: {"label": "Test", "fields": [{"field_key": "email", "label": "Email"}], **kw})
        monkeypatch.setattr(manager, "list_custom_service_relations", lambda **kw: [
            {"id": 7, "source_service_code": "quotes", "target_service_code": "vendors", "is_active": True}])
        monkeypatch.setattr(manager, "list_custom_service_record_relation_links", lambda **kw: [
            {"linked_service_code": "vendors", "linked_record": {"values": {"email": "vendor@example.org"}}}])
        monkeypatch.setattr(manager, "list_custom_service_records", lambda **kw: [{"service_code": "quotes", "id": "r", "values": {}}])
        monkeypatch.setattr(importlib.import_module("monitoring.api.app"), "send_alert_email", deliver)
        for code in ("first", "second"):
            manager.save_notification_template(code=code, label=code, module_code="quotes", task_type="record:preview",
                                               subject_template=code + " {{record.id}}", body_template="Original")
        api = SimpleNamespace(logs=manager, settings_service=SimpleNamespace(get=lambda: SimpleNamespace(smtp_host="test.invalid")))
        app = FastAPI()
        _register_admin_routes(app, lambda: api, lambda: SimpleNamespace(subject="editor"))
        client = TestClient(app)
        path = "/admin/custom-services/quotes/records/r/mail"
        assert len(client.get(path).json()["templates"]) == 2
        prepare = {"revision": 0, "recipient": "first@example.org", "template_code": "second"}
        assert client.post(path + "/prepare", json={**prepare, "template_code": "absent"}).status_code == 422
        draft = client.post(path + "/prepare", json=prepare).json()
        assert (draft["subject"], draft["status"]) == ("second r", "awaiting_approval")
        assert client.post(path + "/cancel?revision=1").json()["status"] == "cancelled"
        prepare["revision"] = 2
        prepare["recipient"] = "{{relation.7.email}}"
        assert client.post(path + "/prepare", json=prepare).json()["status"] == "awaiting_approval"
        edit = {"revision": 3, "recipient": "final@example.org", "subject": "Correction", "body": "Texte ajusté"}
        denied_modules.add(custom_service_module_code("vendors"))
        assert client.get(path).status_code == 403
        assert client.get("/followups").json() == []
        assert client.get("/followups/" + draft["id"]).status_code == 403
        assert client.post(path + "/cancel?revision=3").status_code == 403
        assert client.post(path + "/approve", json=edit).status_code == 403
        denied_modules.clear()
        assert client.post(path + "/approve", json={**edit, "recipient": ""}).status_code == 422
        assert client.post(path + "/save", json={**edit, "recipient": ""}).json()["body"] == edit["body"]
        assert client.post(path + "/approve", json=edit).status_code == 409
        edit["revision"] = 4
        allowed.remove("update")
        assert client.post(path + "/approve", json=edit).status_code == 403
        allowed.add("update")
        assert not deliveries
        result = client.post(path + "/approve", json=edit)
        assert result.status_code == {None: 200, "smtp": 502, "confirmation": 503}[failure], result.text
        assert client.post(path + "/approve", json=edit).status_code == 409
        assert deliveries == [("Correction", "Texte ajusté", ["final@example.org"])]
        final = client.get(path).json()["draft"]
        assert final["status"] == {None: "sent", "smtp": "pending", "confirmation": "sending"}[failure]
        assert bool(final["sent_at"]) == (failure is None)
        assert any(event["actor"] == "editor" and event["note"] == "approve" for event in final["events"])
        if failure == "confirmation":
            monkeypatch.setattr(manager, "cancel_notification_tasks_for_source", lambda **kwargs: 0)
            checked = client.post(f"/provider-requests/{draft['id']}/mark-sent")
            assert checked.status_code == 200, checked.text
            assert checked.json()["status"] == "sent"
            assert len(deliveries) == 1
