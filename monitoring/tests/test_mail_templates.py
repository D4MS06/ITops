from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from monitoring.api.app import _register_admin_routes, _render_notification_task_message
from monitoring.config.settings import NotificationSettings
from monitoring.config.settings_codec import build_notification_settings_kwargs, build_settings_payload
from monitoring.services.mail_templates import ensure_monitoring_mail_template, render_mail_template_text, render_record_preview
from monitoring.services.monitoring_service import MonitoringService
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.services.module_permissions import custom_service_module_code


def test_record_template_preview_reads_only_authorized_direct_relation():
    grants = {custom_service_module_code("requests")}
    links = []
    relation_reads = []

    def relations(**kwargs):
        relation_reads.append(kwargs["service_code"])
        return [{"id": 7, "source_service_code": "requests", "target_service_code": "vendors"}]

    store = SimpleNamespace(
        subject_has_module_permission=lambda **kw: kw["module_code"] in grants,
        get_custom_service=lambda code: {"code": code, "label": code, "fields": [
            {"field_key": "value", "label": "Valeur"}, {"field_key": "password", "label": "Ancien champ"},
        ]},
        list_custom_service_relations=relations,
        list_custom_service_records=lambda **kw: [{"id": "r", "service_code": "requests", "values": {"value": "{record.id}"}}],
        list_custom_service_record_relation_links=lambda **kw: links,
    )
    app = FastAPI()
    _register_admin_routes(app, lambda: SimpleNamespace(logs=store), lambda: SimpleNamespace(subject="reader"))
    client = TestClient(app)
    url = "/notifications/templates/context/requests"
    payload = dict(record_id="r", recipient="free@example.org", subject_template="{record.fields.value}", body_template="{{record.id}}")
    def preview():
        return client.post(url + "/preview", json=payload)

    assert preview().json() == {"recipient": "free@example.org", "subject": "{record.id}", "body": "r"}
    assert relation_reads == []
    payload["recipient"] = "{{relation.7.value}}"
    assert preview().status_code == 403
    assert len(client.get(url).json()) == 1
    grants.add(custom_service_module_code("vendors"))
    assert len(client.get(url).json()) == 2
    payload["subject_template"] = "{{record.fields.password}}"
    assert "Variable indisponible" in preview().json()["detail"]
    payload["subject_template"] = "{record.fields.value}"
    assert preview().status_code == 422
    links.append({"linked_service_code": "vendors", "linked_record": {"values": {"value": "vendor@example.org"}}})
    assert preview().json()["recipient"] == "vendor@example.org"
    for invalid in ("", "invalide"):
        links[0]["linked_record"]["values"]["value"] = invalid
        assert preview().status_code == 422
    links[0]["linked_record"]["values"]["value"] = "vendor@example.org"
    links.append(links[0])
    assert preview().status_code == 422
    grants.clear()
    assert preview().status_code == 403


def test_shared_renderer_accepts_legacy_and_current_variables():
    assert render_mail_template_text("{device_name} / {{device_name}}", {"device_name": "SW01"}) == "SW01 / SW01"


def test_record_preview_rejects_multiline_subject_from_record():
    payload = SimpleNamespace(subject_template="{{record.fields.objet}}", body_template="Texte",
                              recipient="test@example.org")
    service = {"fields": [{"field_key": "objet", "label": "Objet"}]}
    record = {"id": "r", "service_code": "quotes", "values": {"objet": "Sujet\nAutre ligne"}}
    with pytest.raises(ValueError, match="seule ligne"):
        render_record_preview(payload, record, service, lambda _: None)


def test_notification_delivery_rejects_record_preview_template():
    store = SimpleNamespace(find_notification_template=lambda **kwargs: {"task_type": "record:preview"})
    with pytest.raises(ValueError, match="réservé à l’aperçu"):
        _render_notification_task_message(SimpleNamespace(logs=store), {})


def test_template_store_rejects_invalid_recipient_before_database_write():
    manager = object.__new__(MariaDBFileManager)
    with pytest.raises(ValueError, match="Adresse e-mail invalide"):
        manager.save_notification_template(
            code="provider-mail-create", label="Creation", module_code="emails",
            task_type="provider:create", subject_template="Sujet", body_template="Corps",
            recipient="adresse invalide",
        )


def test_provider_default_recipient_survives_settings_round_trip():
    payload = build_settings_payload(NotificationSettings(
        recipients="alerts@example.org", provider_recipient="provider@example.org",
        internal_sender_name="ITops", internal_sender_address="notifications@example.org",
        provider_sender_name="Service informatique", provider_sender_address="demandes@example.org",
    ))
    restored = build_notification_settings_kwargs(payload)
    assert restored["recipients"] == "alerts@example.org"
    assert restored["provider_recipient"] == "provider@example.org"
    assert restored["internal_sender_name"] == "ITops"
    assert restored["internal_sender_address"] == "notifications@example.org"
    assert restored["provider_sender_name"] == "Service informatique"
    assert restored["provider_sender_address"] == "demandes@example.org"


def test_monitoring_uses_central_template_instead_of_legacy_settings():
    rows = [{"code": "monitoring-status-change", "module_code": "monitoring", "task_type": "monitoring:status_change",
             "subject_template": "{{device_name}} : {{new_status}}", "body_template": "IP {{device_ip}}", "is_active": True,
             "is_default": True}]
    store = SimpleNamespace(list_notification_templates=lambda **_kwargs: rows)
    settings = NotificationSettings(monitoring_notification_subject_template="Ancien {device_name}")
    service = MonitoringService(SimpleNamespace(), logs_store=store, notifier_settings_provider=lambda: settings)
    try:
        enabled, subject, body = service._build_monitoring_notification_payload(
            dtype="switch", device=SimpleNamespace(name="SW01", ip="192.0.2.1"),
            old_status="online", new_status="offline",
        )
        assert (enabled, subject, body) == (True, "SW01 : offline", "IP 192.0.2.1")
        rows[0]["is_active"] = False
        assert service._build_monitoring_notification_payload(
            dtype="switch", device=SimpleNamespace(name="SW01", ip="192.0.2.1"),
            old_status="online", new_status="offline",
        ) == (False, "", "")
    finally:
        service.shutdown()


def test_monitoring_template_migration_copies_custom_text_once():
    rows = []
    saved = []
    store = SimpleNamespace(list_notification_templates=lambda **_kwargs: rows,
                            save_notification_template=lambda **values: saved.append(values) or rows.append(values))
    settings = NotificationSettings(monitoring_notification_subject_template="Personnalisé {device_name}",
                                    monitoring_notification_body_template="État {new_status}")
    ensure_monitoring_mail_template(store, settings)
    ensure_monitoring_mail_template(store, settings)
    assert len(saved) == 1
    assert saved[0]["subject_template"] == "Personnalisé {device_name}"
    assert saved[0]["body_template"] == "État {new_status}"
