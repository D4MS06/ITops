import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from monitoring.config.settings import NotificationSettings
from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.storage.sqlite_manager import SQLiteFileManager


class DummyParent:
    def after(self, delay, callback):
        callback()


class DummyView:
    parent = DummyParent()

    def update_display(self):
        pass

    def disable_start_button(self):
        pass

    def enable_stop_button(self):
        pass

    def enable_start_button(self):
        pass

    def disable_stop_button(self):
        pass


def _build_model_with_data(data):
    default_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True, "config_backups_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True, "config_backups_enabled": False},
    ]
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.list_device_types",
        return_value=default_types,
    ), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map",
        return_value=data,
    ):
        manager = SQLiteFileManager.__new__(SQLiteFileManager)
        return DevicesModel(manager=manager)


def _set_clock(controller: AppController, *values: float) -> None:
    ticks = iter(values)
    controller._monitoring_service._clock = lambda: next(ticks)


def test_status_change_triggers_email(tmp_path):
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc"}],
            "switch": [],
        }
    )

    device = model.device_data["server"]["srv1"]
    device.status = "offline"

    view = DummyView()
    controller = AppController(model, view)
    controller.set_offline_delay_seconds(1)
    controller.set_online_recovery_delay_seconds(1)
    controller.set_failures_for_offline(1)
    controller.set_successes_for_online(1)
    controller.set_probe_interval_ms(1000)
    _set_clock(controller, 0.0, 1.2)

    async def fake_ping(ip, timeout=2):
        return None

    aioping_module = type("Aioping", (), {"ping": AsyncMock(side_effect=fake_ping)})

    with (
        patch("monitoring.controllers.app_controller.aioping", aioping_module),
        patch("monitoring.controllers.app_controller.send_alert_email") as send_email,
        patch.object(controller._logs_store, "record_status_log") as record_log,
        patch("monitoring.controllers.app_controller.mb.showinfo"),
    ):
        model.do_run["server"] = True

        ticks = {"count": 0}
        real_sleep = asyncio.sleep

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 2:
                model.do_run["server"] = False
            await real_sleep(0)

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("server"))

        send_email.assert_called_once()
        record_log.assert_called_once()


def test_no_recovery_alert_on_single_success_probe(tmp_path):
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc"}],
            "switch": [],
        }
    )

    device = model.device_data["server"]["srv1"]
    device.status = "offline"

    view = DummyView()
    controller = AppController(model, view)
    controller.set_offline_delay_seconds(5)
    controller.set_online_recovery_delay_seconds(5)
    controller.set_failures_for_offline(1)
    controller.set_successes_for_online(2)
    controller.set_probe_interval_ms(1000)

    async def fake_ping(ip, timeout=2):
        return None

    aioping_module = type("Aioping", (), {"ping": AsyncMock(side_effect=fake_ping)})

    with (
        patch("monitoring.controllers.app_controller.aioping", aioping_module),
        patch("monitoring.controllers.app_controller.send_alert_email") as send_email,
        patch("monitoring.controllers.app_controller.mb.showinfo"),
    ):
        model.do_run["server"] = True

        ticks = {"count": 0}

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 1:
                model.do_run["server"] = False

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("server"))

        send_email.assert_not_called()


def test_notification_cooldown_suppresses_immediate_second_alert(tmp_path):
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc"}],
            "switch": [],
        }
    )

    device = model.device_data["server"]["srv1"]
    device.status = "online"

    view = DummyView()
    controller = AppController(model, view)
    controller.set_offline_delay_seconds(1)
    controller.set_online_recovery_delay_seconds(1)
    controller.set_notification_cooldown_seconds(30)
    controller.set_failures_for_offline(1)
    controller.set_successes_for_online(1)
    controller.set_probe_interval_ms(1000)

    reachability = [False, False, True, True]

    async def fake_reachability(_dev):
        return reachability.pop(0)

    with (
        patch.object(controller, "_is_device_reachable", side_effect=fake_reachability),
        patch("monitoring.controllers.app_controller.send_alert_email") as send_email,
        patch("monitoring.controllers.app_controller.mb.showinfo"),
    ):
        model.do_run["server"] = True

        ticks = {"count": 0}
        real_sleep = asyncio.sleep

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 4:
                model.do_run["server"] = False
            await real_sleep(1.05)

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("server"))

        send_email.assert_called_once()


def test_idle_to_offline_does_not_trigger_status_log_or_notification(tmp_path):
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc"}],
            "switch": [],
        }
    )

    device = model.device_data["server"]["srv1"]
    device.status = "idle"

    view = DummyView()
    controller = AppController(model, view)
    controller.set_offline_delay_seconds(1)
    controller.set_online_recovery_delay_seconds(1)
    controller.set_failures_for_offline(1)
    controller.set_successes_for_online(1)
    controller.set_probe_interval_ms(1000)
    _set_clock(controller, 0.0, 1.2)

    reachability = [False, False]

    async def fake_reachability(_dev):
        return reachability.pop(0)

    with (
        patch.object(controller, "_is_device_reachable", side_effect=fake_reachability),
        patch("monitoring.controllers.app_controller.send_alert_email") as send_email,
        patch.object(controller._logs_store, "record_status_log") as record_log,
        patch("monitoring.controllers.app_controller.mb.showinfo"),
    ):
        model.do_run["server"] = True

        ticks = {"count": 0}
        real_sleep = asyncio.sleep

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 2:
                model.do_run["server"] = False
            await real_sleep(0)

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("server"))

        assert device.status == "offline"
        send_email.assert_not_called()
        record_log.assert_not_called()


def test_dynamic_monitorable_type_triggers_log_and_notification():
    dynamic_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
        {"code": "firewall", "label": "Firewall", "icon": "server", "monitoring_enabled": True},
    ]
    data = {
        "switch": [],
        "server": [],
        "firewall": [{"id": "fw1", "ip": "1.1.1.1", "name": "FW-1", "description": "Edge firewall", "notify": True}],
    }

    with (
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.list_device_types", return_value=dynamic_types),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map", return_value=data),
    ):
        manager = SQLiteFileManager.__new__(SQLiteFileManager)
        model = DevicesModel(manager=manager)

    device = model.device_data["firewall"]["fw1"]
    device.status = "online"
    model.notify_flags.setdefault("firewall", {})["fw1"] = True
    model.do_run["firewall"] = True

    view = DummyView()
    controller = AppController(model, view)
    controller.set_offline_delay_seconds(1)
    controller.set_online_recovery_delay_seconds(1)
    controller.set_failures_for_offline(1)
    controller.set_successes_for_online(1)
    controller.set_probe_interval_ms(1000)
    _set_clock(controller, 0.0, 1.2)

    reachability = [False, False]

    async def fake_reachability(_dev):
        return reachability.pop(0)

    with (
        patch.object(controller, "_is_device_reachable", side_effect=fake_reachability),
        patch("monitoring.controllers.app_controller.send_alert_email") as send_email,
        patch.object(controller._logs_store, "record_status_log") as record_log,
        patch("monitoring.controllers.app_controller.mb.showinfo"),
    ):
        ticks = {"count": 0}
        real_sleep = asyncio.sleep

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 2:
                model.do_run["firewall"] = False
            await real_sleep(0)

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("firewall"))

        send_email.assert_called_once()
        assert record_log.call_count >= 1


def test_controller_delegates_start_stop_to_shared_runtime_service():
    model = _build_model_with_data(
        {
            "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc"}],
            "switch": [],
        }
    )
    view = DummyView()
    runtime = SimpleNamespace(
        start_monitoring=lambda dtype: dtype == "server",
        stop_monitoring=lambda dtype: dtype == "server",
        stop_all=lambda: ["server"],
    )
    controller = AppController(model, view, monitoring_runtime_service=runtime)

    with patch.object(controller, "_refresh_all_views") as refresh_views:
        controller.start_monitoring("server")
        controller.stop_monitoring("server")
        controller.stop_all_monitoring()

    assert refresh_views.call_count == 3


def test_apply_notification_settings_updates_runtime_and_popup_flag():
    model = _build_model_with_data({"server": [], "switch": []})
    controller = AppController(model)
    settings = NotificationSettings(
        offline_delay_seconds=12,
        online_recovery_delay_seconds=9,
        notification_cooldown_seconds=55,
        failures_for_offline=4,
        successes_for_online=3,
        ping_timeout_ms=1800,
        probe_interval_ms=1300,
        log_diagnostic_events=True,
        show_status_popup=False,
    )

    controller.apply_notification_settings(settings)

    service = controller._monitoring_service
    assert service.offline_delay_seconds == 12
    assert service.online_recovery_delay_seconds == 9
    assert service.notification_cooldown_seconds == 55
    assert service.failures_for_offline == 4
    assert service.successes_for_online == 3
    assert service.ping_timeout_ms == 1800
    assert service.probe_interval_ms == 1300
    assert service.log_diagnostic_events is True
    assert controller.show_status_popup is False
