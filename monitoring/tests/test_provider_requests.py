from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _execute_notification_task, _register_admin_routes
from monitoring.services.provider_requests import confirmed_mail_changes, mail_request_changes, mail_request_target, rejected_mail_changes, render_provider_template
from monitoring.services.followup_requests import require_followup_transition, sync_followup_reminder
from monitoring.storage.mariadb_bootstrap import MariaDBBootstrapper


def test_mail_request_changes_keep_alias_pending_until_confirmation():
    record = {"values": {"address": "alice@example.org", "alias": "a@example.org", "status": "Actif"}}
    target = mail_request_target(action="add_alias", record=record, target_value="b@example.org")
    expected, confirmed = mail_request_changes(action="add_alias", record=record, target_value=target)
    assert expected == {"alias": "a@example.org"}
    assert confirmed == {"alias": "a@example.org, b@example.org"}
    assert record["values"]["alias"] == "a@example.org"


def test_mail_creation_preserves_selected_account_type():
    expected, confirmed = mail_request_changes(action="create", record=None, target_value="team@example.org", account_type="partage")
    assert expected == {}
    assert confirmed == {"address": "team@example.org", "type_compte": "partage", "status": "Actif"}


def test_followup_transitions_reject_confirmation_before_sending():
    require_followup_transition("pending", "sent")
    require_followup_transition("sent", "done")
    try:
        require_followup_transition("pending", "done")
    except ValueError:
        pass
    else:
        raise AssertionError("A pending request was confirmed before sending")


def test_shared_followup_reminder_links_to_request_in_any_module():
    scheduled, cancelled = [], []
    store = SimpleNamespace(
        upsert_notification_task=lambda **values: scheduled.append(values),
        cancel_notification_tasks_for_source=lambda **values: cancelled.append(values),
    )
    request = {"id": "request-7", "module_code": "assets", "record_id": "asset-1", "target_value": "Asset 1",
               "reminder_due_at": "2026-11-20 09:00:00", "status": "sent"}
    sync_followup_reminder(store, request)
    assert scheduled[0]["trigger_field_key"] == "followup_request"
    assert scheduled[0]["trigger_value"] == "request-7"
    sync_followup_reminder(store, {**request, "status": "done"})
    assert cancelled[0]["trigger_value"] == "request-7"


def test_closed_followup_reminder_is_cancelled_without_sending(monkeypatch):
    sent = []
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda *_args, **_kwargs: sent.append(True))
    updated = []
    logs = SimpleNamespace(
        get_provider_request=lambda **_kwargs: {"status": "done"},
        set_notification_task_status=lambda **values: updated.append(values) or {"status": values["status"]},
    )
    task = {"id": "task-1", "status": "pending", "trigger_field_key": "followup_request", "trigger_value": "request-7"}
    result = _execute_notification_task(SimpleNamespace(logs=logs), task)
    assert result["status"] == "cancelled"
    assert sent == []


def test_mail_request_rejects_duplicate_alias_and_missing_record():
    record = {"values": {"address": "alice@example.org", "alias": "a@example.org"}}
    try:
        mail_request_target(action="add_alias", record=record, target_value="a@example.org")
    except ValueError as exc:
        assert "déjà présent" in str(exc)
    else:
        raise AssertionError("duplicate alias accepted")
    try:
        mail_request_target(action="delete", record=None, target_value="")
    except ValueError as exc:
        assert "existant" in str(exc)
    else:
        raise AssertionError("missing account accepted")


def test_provider_template_rejects_unknown_variable():
    try:
        render_provider_template({"subject_template": "{{unknown}}", "body_template": "Bonjour"}, {"address": "a@example.org"})
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("unknown variable accepted")


def test_provider_details_are_appended_only_when_entered():
    template = {"subject_template": "Demande {{address}}", "body_template": "Bonjour {{requester}}."}
    variables = {"address": "alice@example.org", "requester": "Alice", "note": ""}
    assert render_provider_template(template, variables) == ("Demande alice@example.org", "Bonjour Alice.")
    variables["note"] = "  Ligne libre\nSans préfixe  "
    assert render_provider_template(template, variables) == (
        "Demande alice@example.org", "Bonjour Alice.\n\n  Ligne libre\nSans préfixe  "
    )


def test_legacy_provider_template_does_not_keep_consigne_label():
    template = {"subject_template": "Demande", "body_template": "Bonjour.\n\nConsignes : {{note}}\n\nMerci."}
    assert render_provider_template(template, {"note": ""}) == ("Demande", "Bonjour.\n\nMerci.")
    assert render_provider_template(template, {"note": "Texte libre"}) == (
        "Demande", "Bonjour.\n\nMerci.\n\nTexte libre"
    )


def test_internal_followup_date_never_appears_in_provider_message():
    template = {
        "subject_template": "Suppression {{address}}",
        "body_template": "Merci de supprimer {{address}}.\n\nDate souhaitée : {{reminder_date}}\n\nConfirmez l'opération.",
    }
    variables = {"address": "alice@example.org", "reminder_date": "", "note": ""}
    assert render_provider_template(template, variables)[1] == "Merci de supprimer alice@example.org.\n\nConfirmez l'opération."
    variables["reminder_date"] = "2026-11-20"
    assert render_provider_template(template, variables)[1] == "Merci de supprimer alice@example.org.\n\nConfirmez l'opération."


def test_starter_template_update_only_matches_unchanged_legacy_bodies():
    statements = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def executemany(self, query, rows):
            statements.append((query, rows))

    connection = SimpleNamespace(cursor=Cursor, commit=lambda: None)
    MariaDBBootstrapper.ensure_provider_mail_templates(connection)
    update_query, update_rows = statements[1]
    assert "WHERE code = %s AND body_template = %s" in update_query
    assert len(update_rows) == 5
    assert all("Consignes" not in new_body for new_body, _code, _old_body in update_rows)
    assert sum("Consignes : {{note}}" in old_body for _new_body, _code, old_body in update_rows) == 4
    assert any(code == "provider-mail-delete" and "Date souhaitée : {{reminder_date}}" in old_body
               for _new_body, code, old_body in update_rows)
    assert all("Date souhaitée" not in new_body for new_body, code, _old_body in update_rows if code == "provider-mail-delete")


def test_confirmation_preserves_new_aliases_only_after_explicit_conflict_acceptance():
    kwargs = dict(action="add_alias", target_value="new@example.org", expected={"alias": "old@example.org"},
                  confirmed={"alias": "old@example.org, new@example.org"},
                  current={"address": "main@example.org", "alias": "old@example.org, concurrent@example.org"})
    try:
        confirmed_mail_changes(**kwargs)
    except ValueError as exc:
        assert "a changé" in str(exc)
    else:
        raise AssertionError("concurrent edit silently overwritten")
    assert confirmed_mail_changes(**kwargs, accept_current=True) == {
        "alias": "old@example.org, concurrent@example.org, new@example.org"
    }


def test_rejected_deletion_restores_initial_status_only_when_unchanged():
    assert rejected_mail_changes(action="delete", current={"status": "A supprimer"},
                                 expected={"status": "A supprimer"}, original={"status": "Actif"}) == {"status": "Actif"}
    try:
        rejected_mail_changes(action="delete", current={"status": "Supprime"},
                              expected={"status": "A supprimer"}, original={"status": "Actif"})
    except ValueError as exc:
        assert "a changé" in str(exc)
    else:
        raise AssertionError("changed status overwritten")


class _Store:
    def __init__(self):
        self.record = {"id": "mail-1", "values": {"address": "alice@example.org", "alias": "", "status": "Actif"}}
        self.requests = {}
        self.template_recipient = "provider@example.org"
        self.template_action = "add_alias"
        self.tasks = []
        self.cancelled_tasks = []

    def get_custom_service(self, *, code):
        return {"code": "emails", "is_active": True, "fields": []} if code == "emails" else None

    def subject_has_module_permission(self, *, subject, module_code, permission):
        return subject == "editor" and module_code == "service_emails" and permission in {"read", "create", "update"}

    def list_custom_service_records(self, *, service_code):
        return [self.record] if service_code == "emails" else []

    def list_notification_templates(self, *, limit=1000):
        subject = "Alias {{alias}}" if self.template_action == "add_alias" else "Suppression {{address}}"
        body = "Créer {{alias}} pour {{address}}." if self.template_action == "add_alias" else "Merci de supprimer {{address}}.\n\nDate souhaitée : {{reminder_date}}\n\nConfirmez l'opération."
        return [{"code": "request-mail", "module_code": "emails", "task_type": f"provider:{self.template_action}", "is_active": True,
                 "is_default": True, "recipient": self.template_recipient, "subject_template": subject,
                 "body_template": body}]

    def upsert_notification_task(self, **values):
        self.tasks.append(values)

    def cancel_notification_tasks_for_source(self, **values):
        self.cancelled_tasks.append(values)

    def create_provider_request(self, **values):
        row = {"id": "request-1", **values, "status": "pending", "resolved_by": "", "resolution_note": ""}
        self.requests[row["id"]] = row
        return row

    def mark_provider_request_sent(self, *, request_id, sent_by=""):
        self.requests[request_id]["status"] = "sent"
        if self.requests[request_id]["action_code"] == "delete":
            self.record["values"]["status"] = "A supprimer"
        return self.requests[request_id]

    def get_provider_request(self, *, request_id):
        return self.requests.get(request_id)

    def resolve_provider_request(self, *, request_id, resolution, resolved_by, note, accept_current=False):
        row = self.requests[request_id]
        row.update(status=resolution, resolved_by=resolved_by, resolution_note=note)
        if resolution == "done":
            if row["action_code"] == "add_alias":
                self.record["values"]["alias"] = row["confirmed_values"]["alias"]
            if row["action_code"] == "delete":
                self.record["values"]["status"] = "Supprime"
        return row

    def list_provider_requests(self, *, module_code, record_id="", limit=1000):
        return [row for row in self.requests.values() if (not module_code or row["module_code"] == module_code) and (not record_id or row["record_id"] == record_id)]


def test_preview_send_and_validation_are_separate(monkeypatch):
    sent = []
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda subject, body, **kwargs: sent.append((subject, body, kwargs["recipients"])))
    store = _Store()
    actor = {"subject": "editor"}
    default_recipient = {"value": "default@example.org"}
    app = FastAPI()
    _register_admin_routes(app, lambda: SimpleNamespace(logs=store, settings_service=SimpleNamespace(get=lambda: SimpleNamespace(smtp_host="smtp.example.org", provider_recipient=default_recipient["value"]))), lambda: SimpleNamespace(subject=actor["subject"]))
    client = TestClient(app)
    payload = {"action_code": "add_alias", "record_id": "mail-1", "target_value": "alias@example.org", "note": "Merci"}

    preview = client.post("/provider-requests/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["recipient"] == "provider@example.org"
    assert store.record["values"]["alias"] == ""

    preview_without_details = client.post("/provider-requests/preview", json={**payload, "note": ""})
    assert preview_without_details.status_code == 200
    assert preview_without_details.json()["body"] == "Créer alias@example.org pour alice@example.org."

    store.template_recipient = ""
    preview_with_default = client.post("/provider-requests/preview", json=payload)
    assert preview_with_default.status_code == 200
    assert preview_with_default.json()["recipient"] == "default@example.org"
    default_recipient["value"] = ""
    assert client.post("/provider-requests/preview", json=payload).status_code == 409
    default_recipient["value"] = "default@example.org"
    store.template_recipient = "provider@example.org"

    created = client.post("/provider-requests", json=payload)
    assert created.status_code == 201
    assert created.json()["status"] == "sent"
    assert client.post("/provider-requests/preview", json=payload).status_code == 409
    assert sent == [("Alias alias@example.org", "Créer alias@example.org pour alice@example.org.\n\nMerci", ["provider@example.org"])]
    assert store.record["values"]["alias"] == ""

    resolved = client.put("/provider-requests/request-1/resolve", json={"resolution": "done"})
    assert resolved.status_code == 200
    assert store.record["values"]["alias"] == "alias@example.org"

    assert len(client.get("/followups").json()) == 1
    assert client.get("/followups/request-1").status_code == 200

    actor["subject"] = "reader"
    forbidden = client.post("/provider-requests/preview", json=payload)
    assert forbidden.status_code == 403
    assert client.get("/followups").json() == []
    assert client.get("/followups/request-1").status_code == 403


def test_deletion_request_without_date_sends_without_scheduling_reminder(monkeypatch):
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda *_args, **_kwargs: None)
    store = _Store()
    store.template_action = "delete"
    app = FastAPI()
    _register_admin_routes(
        app,
        lambda: SimpleNamespace(logs=store, settings_service=SimpleNamespace(get=lambda: SimpleNamespace(smtp_host="smtp.example.org"))),
        lambda: SimpleNamespace(subject="editor"),
    )
    client = TestClient(app)
    payload = {"action_code": "delete", "record_id": "mail-1"}

    preview = client.post("/provider-requests/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["reminder_due_at"] == ""
    assert "Date souhaitée" not in preview.json()["body"]
    created = client.post("/provider-requests", json=payload)
    assert created.status_code == 201
    assert store.tasks == []
    assert store.record["values"]["status"] == "A supprimer"


def test_deletion_request_with_date_keeps_scheduled_reminder(monkeypatch):
    monkeypatch.setattr("monitoring.api.app.send_alert_email", lambda *_args, **_kwargs: None)
    store = _Store()
    store.template_action = "delete"
    app = FastAPI()
    _register_admin_routes(
        app,
        lambda: SimpleNamespace(logs=store, settings_service=SimpleNamespace(get=lambda: SimpleNamespace(smtp_host="smtp.example.org"))),
        lambda: SimpleNamespace(subject="editor"),
    )
    client = TestClient(app)

    created = client.post("/provider-requests", json={"action_code": "delete", "record_id": "mail-1", "reminder_due_at": "2026-11-20"})
    assert created.status_code == 201
    assert store.tasks[0]["due_at"] == "2026-11-20 09:00:00"
    assert "Vérifier" in store.tasks[0]["title"]
    assert "2026-11-20" not in created.json()["body"]
    assert store.tasks[0]["trigger_field_key"] == "followup_request"
    assert store.tasks[0]["trigger_value"] == created.json()["id"]
    assert store.record["values"]["status"] == "A supprimer"

    resolved = client.put(f"/provider-requests/{created.json()['id']}/resolve", json={"resolution": "done"})
    assert resolved.status_code == 200
    assert store.record["values"]["status"] == "Supprime"
    assert any(item["trigger_field_key"] == "followup_request" and item["trigger_value"] == created.json()["id"]
               for item in store.cancelled_tasks)
