from contextlib import contextmanager, nullcontext
import importlib
import json
import os
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from monitoring.api.app import _execute_custom_service_automation_event, _register_admin_routes
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.services.module_permissions import custom_service_module_code
from scripts.configure_devis_automations import quote_rules, quote_validation_rules


pytestmark = pytest.mark.skipif(os.getenv("ITOPS_TEST_MARIADB") != "1", reason="requires the ITops MariaDB schema")


@contextmanager
def temporary_automation_store(monkeypatch, source, target, relation):
    manager = MariaDBFileManager()
    with manager._connect() as conn:
        with conn.cursor() as cursor:
            for table in ("custom_service_records", "provider_requests", "custom_service_children", "custom_service_record_history",
                          "custom_service_relation_links", "custom_service_record_index"):
                if table == "custom_service_record_index":
                    cursor.execute(f"CREATE TEMPORARY TABLE schema_{table} ENGINE=InnoDB AS SELECT * FROM {table} LIMIT 0")
                    cursor.execute(f"ALTER TABLE schema_{table} ADD PRIMARY KEY(record_id)")
                else:
                    cursor.execute(f"CREATE TEMPORARY TABLE schema_{table} LIKE {table}")
                cursor.execute(f"CREATE TEMPORARY TABLE {table} LIKE schema_{table}")
        monkeypatch.setattr(manager, "_open_connection", lambda: nullcontext(conn))
        monkeypatch.setattr(manager, "_bootstrap_completed", True)
        monkeypatch.setattr(manager, "get_custom_service", lambda code: source if code == source["code"] else target)
        monkeypatch.setattr(manager, "list_custom_service_relations", lambda **_: [relation])
        monkeypatch.setattr(manager, "_get_custom_service_relation_by_id", lambda **_: relation)
        monkeypatch.setattr(manager, "save_automation_execution_log", lambda **_: None)
        yield manager


def test_quote_workflow_atomic_creation_and_existing_order(monkeypatch):
    source_code, target_code = "demandes_de_devis", "commandes_informatiques"
    source = {"code": source_code, "label": "Demande", "fields": [], "automation_rules": quote_rules(1)}
    target = {"code": target_code, "label": "Commande", "is_active": True, "fields": []}
    for service, keys in [(source, "objet categorie priorite mode_achat date_envoi date_reception_devis statut suite_demande"),
                          (target, "objet categorie priorite mode_achat date_demande_devis date_reception_devis statut")]:
        service["fields"] = [{"field_key": k, "label": k, "required": k == "categorie"} for k in keys.split()]
    relation = {"id": 1, "cardinality": "one_to_one", "source_service_code": source_code,
                "target_service_code": target_code, "is_active": True}
    with temporary_automation_store(monkeypatch, source, target, relation) as manager:
        allowed = {"read", "update", "create"}

        def authorize(code, permission):
            assert code == target_code
            if permission not in allowed:
                raise HTTPException(403)

        def event(kind, record_id="r"):
            with manager.record_automation_transaction(service_code=source_code, record_id=record_id) as store:
                record, = store.list_custom_service_records(service_code=source_code, record_id=record_id)
                return _execute_custom_service_automation_event(store, service=source, record=record, actor="test",
                    authorize=authorize, event={"type": kind, "field_key": "reference_devis" if kind == "document_linked" else "",
                                                "sent_at": "2026-11-01", "linked_at": "2026-11-04"})

        values = {"objet": "Test", "suite_demande": "Circuit d'achat", "statut": "Brouillon"}
        manager.save_custom_service_record(service_code=source_code, record_id="r", values=values, children=[])
        source["treeview_config"] = json.dumps({"automation_rules": source["automation_rules"],
                                               "validation_rules": quote_validation_rules()})
        manager.save_custom_service_record(service_code=source_code, record_id="unsent",
            values={**values, "categorie": "Matériel"}, children=[])
        with pytest.raises(HTTPException) as unsent:
            event("document_linked", "unsent")
        assert unsent.value.status_code == 422
        assert not manager.list_custom_service_records(service_code=target_code)
        assert manager.list_custom_service_records(service_code=source_code, record_id="unsent")[0]["values"]["statut"] == "Brouillon"
        blocked = set()
        monkeypatch.setattr(manager, "subject_has_module_permission", lambda **kw: kw["permission"] in allowed and kw["module_code"] not in blocked)
        monkeypatch.setattr(manager, "get_notification_template", lambda code: {"code": code, "is_active": True,
            "module_code": source_code, "task_type": "record:preview", "subject_template": "Test", "body_template": "Bonjour"})
        deliveries = []
        monkeypatch.setattr(importlib.import_module("monitoring.api.app"), "send_alert_email", lambda *args, **kwargs: deliveries.append(args))
        app = FastAPI()
        _register_admin_routes(app, lambda: SimpleNamespace(logs=manager, settings_service=SimpleNamespace(
            get=lambda: SimpleNamespace(smtp_host="smtp.invalid"))), lambda: SimpleNamespace(subject="test"))
        client = TestClient(app)
        path = f"/admin/custom-services/{source_code}/records/r/mail"
        assert client.post(path + "/prepare", json={"template_code": "exemple", "revision": 0}).status_code == 200
        assert manager.list_custom_service_records(service_code=source_code, record_id="r")[0]["values"]["statut"] == "À valider"
        approval = {"revision": 1, "subject": "Test", "body": "Bonjour", "recipient": "test@example.org"}
        blocked.add(custom_service_module_code(target_code))
        assert client.post(path + "/approve", json=approval).status_code == 403
        assert deliveries == []
        blocked.clear()
        response = client.post(path + "/approve", json=approval)
        assert response.status_code == 200, response.text
        assert len(deliveries) == 1
        sent = manager.list_custom_service_records(service_code=source_code, record_id="r")[0]["values"]
        assert sent["statut"] == "En attente du devis" and sent["date_envoi"] == response.json()["sent_at"][:10]
        with pytest.raises(HTTPException, match="categorie"):
            event("document_linked")
        assert not manager.list_custom_service_records(service_code=target_code)
        assert manager.list_custom_service_records(service_code=source_code, record_id="r")[0]["values"] == sent
        manager.save_custom_service_record(service_code=source_code, record_id="r", values={**sent, "categorie": "Matériel"}, children=[])
        allowed.remove("create")
        with pytest.raises(HTTPException) as denied:
            event("document_linked")
        assert denied.value.status_code == 403
        allowed.add("create")
        def fail_link(**kwargs):
            raise RuntimeError("Liaison interrompue")

        with monkeypatch.context() as patch:
            patch.setattr(manager, "save_custom_service_record_relation_link", fail_link)
            with pytest.raises(RuntimeError, match="Liaison interrompue"):
                event("document_linked")
        assert not manager.list_custom_service_records(service_code=target_code)
        event("document_linked")
        event("document_linked")
        order, = manager.list_custom_service_records(service_code=target_code)
        assert order["values"]["date_reception_devis"] == "2026-11-04"
        assert order["values"]["statut"] == "Devis reçu"
        assert order["values"]["date_demande_devis"] == sent["date_envoi"]
        waiting = {**order["values"], "statut": "Demande de devis", "objet": "Objet ajusté", "date_reception_devis": ""}
        manager.save_custom_service_record(service_code=target_code, record_id=order["id"], values=waiting, children=[])
        event("document_linked")
        existing, = manager.list_custom_service_records(service_code=target_code)
        assert existing["id"] == order["id"] and existing["values"]["objet"] == "Objet ajusté"
        assert existing["values"]["statut"] == "Devis reçu" and existing["values"]["date_reception_devis"] == "2026-11-04"
        later = {**order["values"], "statut": "Bon de commande émis"}
        manager.save_custom_service_record(service_code=target_code, record_id=order["id"], values=later, children=[])
        event("document_linked")
        assert manager.list_custom_service_records(service_code=target_code)[0]["values"] == later
        manager.save_custom_service_record(service_code=source_code, record_id="free",
            values={**values, "suite_demande": "Suivi uniquement", "date_envoi": sent["date_envoi"]}, children=[])
        assert event("document_linked", "free")["values"]["statut"] == "Devis reçu"
        assert len(manager.list_custom_service_records(service_code=target_code)) == 1


def test_orders_update_only_their_linked_commitment(monkeypatch):
    source = {"code": "commandes_informatiques", "label": "Commandes", "fields": [{"field_key": "objet"}]}
    target = {"code": "engagements", "label": "Engagements", "is_active": True, "fields": [{"field_key": "objet"}]}
    relation = {"id": 39, "cardinality": "many_to_one", "source_service_code": source["code"],
                "target_service_code": target["code"], "is_active": True}
    mapping = {"objet": {"source": "objet", "existing": "empty"}}
    action = {"type": "write_linked_record", "relation_id": "39", "create_if_missing": False, "mapping": mapping}
    source["automation_rules"] = [{"trigger": {"type": "document_linked", "field_key": "devis"}, "actions": [action]}]
    with temporary_automation_store(monkeypatch, source, target, relation) as manager:
        def receive(record_id):
            with manager.record_automation_transaction(service_code=source["code"], record_id=record_id) as store:
                row, = store.list_custom_service_records(service_code=source["code"], record_id=record_id)
                _execute_custom_service_automation_event(store, service=source, record=row, actor="test",
                    authorize=lambda code, permission: None, event={"type": "document_linked", "field_key": "devis"})

        for key in ("A", "B", "C"):
            manager.save_custom_service_record(service_code=source["code"], record_id=key, values={"objet": key}, children=[])
        receive("A")
        assert not manager.list_custom_service_records(service_code=target["code"])
        action["create_if_missing"] = True
        receive("A")
        shared, = manager.list_custom_service_records(service_code=target["code"])
        manager.save_custom_service_record_relation_link(service_code=source["code"], record_id="B",
            relation_id=39, linked_record_id=shared["id"])
        receive("B")
        assert manager.list_custom_service_records(service_code=target["code"])[0]["values"]["objet"] == "A"
        mapping["objet"]["existing"] = "replace"
        receive("B")
        receive("C")
        receive("C")
        records = manager.list_custom_service_records(service_code=target["code"])
        assert len(records) == 2
        assert {r["values"]["objet"] for r in records} == {"B", "C"}
        assert next(r for r in records if r["id"] == shared["id"])["values"]["objet"] == "B"
        for multiple in ("one_to_many", "many_to_many"):
            relation["cardinality"] = multiple
            with pytest.raises(HTTPException, match="cible unique"):
                receive("A")
