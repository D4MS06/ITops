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

        model = DevicesModel(manager=mgr)
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


def test_dynamic_type_has_monitoring_and_notify_buckets_when_monitorable():
    dynamic_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
        {"code": "firewall", "label": "Firewall", "icon": "server", "monitoring_enabled": True},
    ]
    data = {"switch": [], "server": [], "firewall": []}

    with (
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.list_device_types", return_value=dynamic_types),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map", return_value=data),
    ):
        manager = SQLiteFileManager.__new__(SQLiteFileManager)
        model = DevicesModel(manager=manager)

    assert "firewall" in model.type_definitions
    assert "firewall" in model.do_run
    assert model.do_run["firewall"] is False
    assert "firewall" in model.notify_flags
    assert isinstance(model.notify_flags["firewall"], dict)
    assert "firewall" in model.device_data


def test_dynamic_type_without_monitoring_has_notify_bucket_but_no_do_run():
    dynamic_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
        {"code": "camera", "label": "Camera", "icon": "server", "monitoring_enabled": False},
    ]
    data = {"switch": [], "server": [], "camera": []}

    with (
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.list_device_types", return_value=dynamic_types),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map", return_value=data),
    ):
        manager = SQLiteFileManager.__new__(SQLiteFileManager)
        model = DevicesModel(manager=manager)

    assert "camera" in model.type_definitions
    assert "camera" not in model.do_run
    assert "camera" in model.notify_flags
    assert isinstance(model.notify_flags["camera"], dict)
    assert "camera" in model.device_data


def test_config_backup_capability_follows_type_flag():
    dynamic_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True, "config_backups_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True, "config_backups_enabled": False},
        {"code": "camera", "label": "Camera", "icon": "server", "monitoring_enabled": False, "config_backups_enabled": True},
    ]
    data = {"switch": [], "server": [], "camera": []}

    with (
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.list_device_types", return_value=dynamic_types),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map", return_value=data),
    ):
        manager = SQLiteFileManager.__new__(SQLiteFileManager)
        model = DevicesModel(manager=manager)

    assert model.is_config_download_type("switch") is True
    assert model.is_config_download_type("server") is False
    assert model.is_config_download_type("camera") is True


def test_refresh_type_definitions_prunes_removed_type_buckets():
    initial_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
        {"code": "camera", "label": "Camera", "icon": "switch", "monitoring_enabled": False},
    ]
    after_types = [
        {"code": "switch", "label": "Switch", "icon": "switch", "monitoring_enabled": True},
        {"code": "server", "label": "Serveur", "icon": "server", "monitoring_enabled": True},
    ]
    data = {"switch": [], "server": [], "camera": []}

    with (
        patch(
            "monitoring.storage.sqlite_manager.SQLiteFileManager.list_device_types",
            side_effect=[initial_types, initial_types, after_types],
        ),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.read_devices_map", return_value=data),
    ):
        manager = SQLiteFileManager.__new__(SQLiteFileManager)
        model = DevicesModel(manager=manager)
        assert "camera" in model.device_data
        model.refresh_type_definitions()

    assert "camera" not in model.device_data
    assert "camera" not in model.notify_flags
