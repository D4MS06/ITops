import asyncio
from unittest.mock import AsyncMock, patch

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel


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
    with patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map",
        return_value=data,
    ):
        return DevicesModel()


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
        real_sleep = asyncio.sleep

        async def fake_sleep(delay):
            ticks["count"] += 1
            if ticks["count"] >= 2:
                model.do_run["server"] = False
            await real_sleep(1.05)

        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("server"))

        send_email.assert_called_once()


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
