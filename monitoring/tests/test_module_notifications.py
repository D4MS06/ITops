from contextlib import nullcontext
import json
import os
from types import SimpleNamespace

import pytest

from monitoring.api.app import _automation_task_recipient_spec, _automation_email_recipients, _execute_notification_task, _notification_task_template_type
from monitoring.services.automation_engine import normalize_rule
from monitoring.services.module_notifications import ModuleNotificationBlocked, module_followup_recipients
from monitoring.services.module_permissions import FOLLOWUP_NOTIFICATION_PERMISSION, custom_service_module_code
from monitoring.storage.mariadb_manager import MariaDBFileManager


def followup_store():
    return SimpleNamespace(
        get_custom_service=lambda **kwargs: {"code": kwargs["code"], "is_active": True},
        list_custom_service_records=lambda **kwargs: [{"id": kwargs["record_id"]}],
        list_module_followup_subjects=lambda **kwargs: ["alice", "bob"],
        list_directory_notification_contacts=lambda: [
            {"identifiers": ["alice", "alice@example.org"], "email": "Alice@example.org"},
            {"identifiers": ["bob"], "email": "bob@example.org"},
            {"identifiers": ["outsider"], "email": "outsider@example.org"},
        ],
    )


def followup_task():
    return {"id": "task", "status": "pending", "source_service_code": "quotes", "source_record_id": "q",
            "trigger_field_key": "automation", "trigger_value": "scheduled:generic:reminder:notify:module_followup:",
            "title": "Devis à suivre", "message": "Vérifiez la demande."}


def test_routing_preserves_colons_in_templates_and_recipient_values():
    task = followup_task()
    assert _notification_task_template_type(task) == "generic:reminder"
    assert _automation_task_recipient_spec(task) == ("module_followup", "")
    task["trigger_value"] = "scheduled:generic:reminder:email:service:agents:mail"
    assert _automation_task_recipient_spec(task) == ("service", "agents:mail")
    assert _notification_task_template_type(task) == "generic:reminder"


def test_followup_recipient_configuration_cannot_target_a_different_module():
    rule = normalize_rule({"trigger": {"type": "record_created"}, "actions": [
        {"type": "notify", "recipient_kind": "module_followup", "recipient_value": "other_module"},
    ]})
    assert rule["actions"][0]["recipient_value"] == ""


def test_followup_contacts_are_deduplicated_without_reading_other_modules():
    store = followup_store()
    contacts = store.list_directory_notification_contacts()
    contacts.append({"identifiers": ["alice"], "email": "alice@example.org"})
    store.list_directory_notification_contacts = lambda: contacts
    assert module_followup_recipients(store, service_code="quotes", record_id="q") == ["alice@example.org", "bob@example.org"]
    contacts[1]["email"] = "ALICE@example.org"
    assert module_followup_recipients(store, service_code="quotes", record_id="q") == ["alice@example.org"]


@pytest.mark.parametrize("problem", ["no_subscribers", "missing_email", "ambiguous_email", "inactive_module", "deleted_record"])
def test_followup_never_falls_back_to_global_recipients(monkeypatch, problem):
    store = followup_store()
    if problem == "no_subscribers":
        store.list_module_followup_subjects = lambda **kwargs: []
    elif problem == "missing_email":
        store.list_directory_notification_contacts = lambda: []
    elif problem == "ambiguous_email":
        store.list_directory_notification_contacts = lambda: [
            {"identifiers": ["alice"], "email": "a@example.org"},
            {"identifiers": ["alice"], "email": "b@example.org"},
        ]
    elif problem == "inactive_module":
        store.get_custom_service = lambda **kwargs: {"is_active": False}
    else:
        store.list_custom_service_records = lambda **kwargs: []
    updates, sent = [], []
    store.set_notification_task_status = lambda **kwargs: updates.append(kwargs)
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda *args, **kwargs: sent.append(kwargs))
    services = SimpleNamespace(logs=store, settings_service=SimpleNamespace(get=lambda: SimpleNamespace(recipients="global@example.org")))
    with pytest.raises(ModuleNotificationBlocked):
        _execute_notification_task(services, followup_task())
    assert sent == []
    assert updates == [{"task_id": "task", "status": "blocked"}]


def test_delivery_rechecks_the_subscription_at_execution_time(monkeypatch):
    store = followup_store()
    store.list_module_followup_subjects = lambda **kwargs: ["bob"]
    sent = []
    store.set_notification_task_status = lambda **kwargs: kwargs
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda *args, **kwargs: sent.append(kwargs))
    services = SimpleNamespace(logs=store, settings_service=SimpleNamespace(get=lambda: object()))
    assert _execute_notification_task(services, followup_task())["status"] == "sent"
    assert sent[0]["recipients"] == ["bob@example.org"]


@pytest.mark.parametrize("kind", ["role", "user", "address", "field", "service"])
def test_unresolved_explicit_recipient_cannot_use_the_global_recipient_list(monkeypatch, kind):
    store = followup_store()
    store.set_notification_task_status = lambda **kwargs: kwargs
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda *args, **kwargs: pytest.fail("Unexpected delivery"))
    task = {**followup_task(), "trigger_value": f"scheduled::notify:{kind}:"}
    with pytest.raises(ModuleNotificationBlocked):
        _execute_notification_task(SimpleNamespace(logs=store), task)


def test_explicit_role_recipients_require_active_accounts_and_source_read_access():
    users = [
        {"subject": "alice", "is_active": True, "role_codes": ["tech"]},
        {"subject": "bob", "is_active": False, "role_codes": ["tech"]},
        {"subject": "private", "is_active": True, "role_codes": ["tech"]},
    ]
    store = SimpleNamespace(
        list_auth_users=lambda: users,
        subject_has_module_permission=lambda **kwargs: kwargs["subject"] != "private",
        list_custom_services=lambda: [{"code": "contacts"}],
        list_custom_service_records=lambda **kwargs: [
            {"values": {"login": user["subject"], "mail": user["subject"] + "@example.org"}} for user in users
        ],
    )
    task = {**followup_task(), "trigger_value": "scheduled::notify:role:tech"}
    assert _automation_email_recipients(SimpleNamespace(logs=store), task) == ["alice@example.org"]


def test_directory_contacts_exclude_disabled_agents_and_use_canonical_mappings():
    manager = object.__new__(MariaDBFileManager)
    manager.list_sync_source_cache_entries = lambda **kwargs: [
        {"external_id": "a", "payload": {"sAMAccountName": "alice", "mail": "alice@example.org", "userAccountControl": "512"}},
        {"external_id": "b", "payload": {"sAMAccountName": "disabled", "mail": "disabled@example.org", "userAccountControl": "514"}},
    ]
    manager.list_manual_directory_users = lambda: [
        {"login": "bob", "email": "bob@example.org", "status": "Actif"},
        {"login": "removed", "email": "removed@example.org", "status": "Corbeille"},
    ]
    assert manager.list_directory_notification_contacts() == [
        {"identifiers": ["alice", ""], "email": "alice@example.org"},
        {"identifiers": ["bob"], "email": "bob@example.org"},
    ]


@pytest.mark.skipif(os.getenv("ITOPS_TEST_MARIADB") != "1", reason="requires ITops MariaDB")
def test_live_role_subscriptions_and_blocked_tasks_on_temporary_tables(monkeypatch):
    manager = MariaDBFileManager()
    module = custom_service_module_code("quotes")
    other = custom_service_module_code("orders")
    with manager._connect() as conn:
        with conn.cursor() as cursor:
            for table in ("auth_users", "auth_modules", "auth_user_roles", "auth_role_modules", "notification_tasks"):
                cursor.execute(f"CREATE TEMPORARY TABLE schema_{table} LIKE {table}")
                cursor.execute(f"CREATE TEMPORARY TABLE {table} LIKE schema_{table}")
            cursor.executemany("INSERT INTO auth_users(subject,password_hash,is_active) VALUES(%s,'test',%s)",
                               [("alice", 1), ("bob", 1), ("disabled", 0), ("legacy", 1), ("admin", 1)])
            cursor.executemany("INSERT INTO auth_modules(code,label,route_path) VALUES(%s,'Test','/')", [(module,), (other,)])
            cursor.executemany("INSERT INTO auth_user_roles(subject,role_code) VALUES(%s,%s)",
                               [("alice", "tech"), ("alice", "backup"), ("bob", "reader"), ("disabled", "tech"), ("legacy", "old"), ("admin", "admin")])
            cursor.executemany("INSERT INTO auth_role_modules(role_code,module_code,permissions_json) VALUES(%s,%s,%s)",
                               [("tech", module, json.dumps([FOLLOWUP_NOTIFICATION_PERMISSION])),
                                ("backup", module, json.dumps(["read", FOLLOWUP_NOTIFICATION_PERMISSION])),
                                ("reader", module, '["read","update"]'), ("old", module, '{}'),
                                ("tech", other, '["read"]')])
        monkeypatch.setattr(manager, "_open_connection", lambda: nullcontext(conn))
        monkeypatch.setattr(manager, "_bootstrap_completed", True)
        assert manager.list_module_followup_subjects(module_code=module) == ["alice"]
        assert manager.list_module_followup_subjects(module_code=other) == []
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM auth_user_roles WHERE subject='alice' AND role_code='tech'")
        assert manager.list_module_followup_subjects(module_code=module) == ["alice"]
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM auth_user_roles WHERE subject='alice'")
        assert manager.list_module_followup_subjects(module_code=module) == []
        with conn.cursor() as cursor:
            cursor.execute("UPDATE auth_modules SET is_active=0 WHERE code=%s", (module,))
        assert manager.list_module_followup_subjects(module_code=module) == []
        task_args = dict(source_service_code="quotes", source_record_id="q", trigger_field_key="automation",
                         trigger_value="scheduled::notify:module_followup:", title="Suivi", message="Suivi", due_at="2026-11-27 09:00:00")
        task = manager.upsert_notification_task(**task_args)
        manager.set_notification_task_status(task_id=task["id"], status="blocked")
        assert manager.upsert_notification_task(**task_args)["status"] == "blocked"
        manager.set_notification_task_status(task_id=task["id"], status="pending")
        assert manager.upsert_notification_task(**task_args)["status"] == "pending"
