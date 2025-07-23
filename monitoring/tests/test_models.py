import json
from unittest.mock import patch

from monitoring.models.devices_model import DevicesModel


def test_add_update_delete_device(tmp_path):
    json_file = tmp_path / "devices.json"
    json_file.write_text(json.dumps({"switch": [], "server": []}))

    fake_init = lambda self, filename="devices.json": setattr(self, "filepath", str(json_file)) or None

    with patch("monitoring.storage.json_manager.JSONFileManager.__init__", fake_init):
        model = DevicesModel()
        assert model.device_data == {"switch": {}, "server": {}}

        dev_id = model.add_device("switch", "SW1", "1.1.1.1", "desc")
        assert dev_id in model.device_data["switch"]
        data = json.loads(json_file.read_text())
        assert any(d["id"] == dev_id for d in data["switch"])

        updated = model.update_device("switch", dev_id, "SW2", "1.1.1.2", "desc2", notify=False)
        assert updated is True
        data = json.loads(json_file.read_text())
        entry = next(d for d in data["switch"] if d["id"] == dev_id)
        assert entry["name"] == "SW2"
        assert entry["ip"] == "1.1.1.2"
        assert entry["notify"] is False
        assert model.device_data["switch"][dev_id].name == "SW2"
        assert model.notify_flags["switch"][dev_id] is False

        deleted = model.delete_device("switch", dev_id)
        assert deleted is True
        data = json.loads(json_file.read_text())
        assert not data["switch"]
        assert dev_id not in model.device_data["switch"]
