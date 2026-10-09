from types import SimpleNamespace

from monitoring.config.settings import NotificationSettings
from monitoring.services.monitoring_service import MonitoringService


def test_monitoring_service_uses_less_sensitive_defaults():
    service = MonitoringService(SimpleNamespace(), logs_store=SimpleNamespace())
    try:
        assert service.offline_delay_seconds == 20
        assert service.online_recovery_delay_seconds == 10
        assert service.failures_for_offline == 5
        assert service.successes_for_online == 3
        assert service.ping_timeout_ms == 2500
        assert service.probe_interval_ms == 2000
    finally:
        service.shutdown()


def test_monitoring_service_applies_runtime_settings():
    service = MonitoringService(SimpleNamespace(), logs_store=SimpleNamespace())
    try:
        service.apply_notification_settings(
            NotificationSettings(
                offline_delay_seconds=30,
                online_recovery_delay_seconds=12,
                failures_for_offline=6,
                successes_for_online=4,
                ping_timeout_ms=3200,
                probe_interval_ms=2500,
                log_diagnostic_events=True,
            )
        )

        assert service.offline_delay_seconds == 30
        assert service.online_recovery_delay_seconds == 12
        assert service.failures_for_offline == 6
        assert service.successes_for_online == 4
        assert service.ping_timeout_ms == 3200
        assert service.probe_interval_ms == 2500
        assert service.log_diagnostic_events is True
    finally:
        service.shutdown()
