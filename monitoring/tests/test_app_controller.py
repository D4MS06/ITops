import json
import asyncio
from unittest.mock import patch, AsyncMock

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


def test_status_change_triggers_email(tmp_path):
    data = {
        "server": [{"id": "srv1", "ip": "1.1.1.1", "name": "Server1", "description": "Desc"}],
        "switch": [],
    }
    json_file = tmp_path / "devices.json"
    json_file.write_text(json.dumps(data))

    def fake_init(self, filename="devices.json"):
        self.filepath = str(json_file)

    with patch("monitoring.storage.json_manager.JSONFileManager.__init__", fake_init):
        model = DevicesModel()

    device = model.device_data["server"]["srv1"]
    device.status = "offline"

    view = DummyView()
    controller = AppController(model, view)

    async def fake_ping(ip, timeout=2):
        return None

    aioping_module = type("Aioping", (), {"ping": AsyncMock(side_effect=fake_ping)})

    with (
        patch("monitoring.controllers.app_controller.aioping", aioping_module),
        patch("monitoring.controllers.app_controller.send_alert_email") as send_email,
        patch("monitoring.controllers.app_controller.mb.showinfo")
    ):
        model.do_run["server"] = True

        async def fake_sleep(delay):
            model.do_run["server"] = False
        with patch("asyncio.sleep", new=fake_sleep):
            asyncio.run(controller._monitor_devices("server"))

        send_email.assert_called_once()
