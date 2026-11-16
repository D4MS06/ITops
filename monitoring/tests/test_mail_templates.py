from types import SimpleNamespace

import pytest

from monitoring.config.settings import NotificationSettings
from monitoring.config.settings_codec import build_notification_settings_kwargs, build_settings_payload
from monitoring.services.mail_templates import ensure_monitoring_mail_template, render_mail_template_text
from monitoring.services.monitoring_service import MonitoringService
from monitoring.storage.mariadb_manager import MariaDBFileManager


def test_shared_renderer_accepts_legacy_and_current_variables():
    assert render_mail_template_text("{device_name} / {{device_name}}", {"device_name": "SW01"}) == "SW01 / SW01"


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
