from unittest.mock import patch

from monitoring.models.devices_model import DevicesModel
from monitoring.storage.sqlite_manager import SQLiteFileManager


def test_add_update_delete_device(tmp_path):
    db_path = tmp_path / "devices.db"

    def fake_init(self, db_name="devices.db"):
        self.data_dir = str(tmp_path)
        self.db_path = str(db_path)

    with patch("monitoring.storage.sqlite_manager.SQLiteFileManager.__init__", fake_init), patch(
        "monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json", lambda self, conn: None
    ):
        mgr = SQLiteFileManager()
        mgr.write_devices_map({"switch": [], "server": []})

        model = DevicesModel()
        assert model.device_data == {"switch": {}, "server": {}}

        dev_id = model.add_device("switch", "SW1", "1.1.1.1", "desc")
        assert dev_id in model.device_data["switch"]
        data = mgr.read_devices_map()
        assert any(d["id"] == dev_id for d in data["switch"])

        updated = model.update_device("switch", dev_id, "SW2", "1.1.1.2", "desc2", notify=False)
        assert updated is True
        data = mgr.read_devices_map()
        entry = next(d for d in data["switch"] if d["id"] == dev_id)
        assert entry["name"] == "SW2"
        assert entry["ip"] == "1.1.1.2"
        assert entry["notify"] is False
        assert model.device_data["switch"][dev_id].name == "SW2"
        assert model.notify_flags["switch"][dev_id] is False

        deleted = model.delete_device("switch", dev_id)
        assert deleted is True
        data = mgr.read_devices_map()
        assert not data["switch"]
        assert dev_id not in model.device_data["switch"]
