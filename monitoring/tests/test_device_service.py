from unittest.mock import patch

import pytest

from monitoring.models.device import Device
from monitoring.services.device_service import DeviceService
from monitoring.storage.sqlite_manager import SQLiteFileManager


def _build_service(tmp_path):
    db_path = tmp_path / "devices.db"

    def fake_init(self, db_name="devices.db"):
        self.data_dir = str(tmp_path)
        self.db_path = str(db_path)

    return (
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager.__init__", fake_init),
        patch("monitoring.storage.sqlite_manager.SQLiteFileManager._seed_from_json", lambda self, conn: None),
    )


def test_device_service_create_update_delete_and_search(tmp_path):
    patch_init, patch_seed = _build_service(tmp_path)
    with patch_init, patch_seed:
        mgr = SQLiteFileManager()
        mgr.write_devices_map({"switch": [], "server": []})
        service = DeviceService(mgr)
        type_definitions = service.list_type_definitions()
        device_data, notify_flags = service.build_device_inventory(type_definitions=type_definitions)

        created = service.create_device(
            type_definitions=type_definitions,
            existing_devices=device_data,
            device_type="server",
            name="Srv Web",
            ip="10.0.0.10",
            description="Frontend",
            web_url="https://srv-web.local",
            custom_data={"site": "Paris"},
            notify=False,
        )

        assert created is not None
        device_data["server"][created.device_id] = created.device
        notify_flags["server"][created.device_id] = created.notify

        listed = service.list_devices(device_data=device_data, notify_flags=notify_flags, device_type="server")
        assert listed[0]["name"] == "Srv Web"
        assert listed[0]["web_url"] == "https://srv-web.local"
        assert listed[0]["custom_data"]["site"] == "Paris"
        assert listed[0]["notify"] is False

        updated = service.update_device(
            type_definitions=type_definitions,
            existing_devices=device_data,
            device_type="server",
            device_id=created.device_id,
            current_device=device_data["server"][created.device_id],
            new_name="Srv API",
            new_ip="10.0.0.11",
            new_description="Backend",
            custom_data={"role": "api"},
            notify=True,
        )

        assert updated is not None
        notify_flags["server"][created.device_id] = updated.notify
        results = service.search_devices(device_data=device_data, notify_flags=notify_flags, query="api")
        assert len(results) == 1
        assert results[0]["name"] == "Srv API"
        assert results[0]["custom_data"] == {"role": "api"}

        assert service.delete_device(device_id=created.device_id) is True
        assert mgr.read_devices_map()["server"] == []


def test_device_service_rejects_duplicate_ip_in_same_type(tmp_path):
    patch_init, patch_seed = _build_service(tmp_path)
    with patch_init, patch_seed:
        mgr = SQLiteFileManager()
        service = DeviceService(mgr)
        type_definitions = service.list_type_definitions()
        existing_devices = {"switch": {"sw1": Device(ip="1.1.1.1", name="SW1", description="", device_type="switch", device_id="sw1")}}

        with pytest.raises(ValueError, match="Adresse IP deja utilisee"):
            service.create_device(
                type_definitions=type_definitions,
                existing_devices=existing_devices,
                device_type="switch",
                name="SW2",
                ip="1.1.1.1",
                description="dup",
            )


def test_device_service_rejects_action_not_allowed_for_os(tmp_path):
    patch_init, patch_seed = _build_service(tmp_path)
    with patch_init, patch_seed:
        mgr = SQLiteFileManager()
        service = DeviceService(mgr)
        type_definitions = service.list_type_definitions()
        existing_devices = {"server": {}}

        with pytest.raises(ValueError, match="Action double-clic"):
            service.create_device(
                type_definitions=type_definitions,
                existing_devices=existing_devices,
                device_type="server",
                name="Srv Linux",
                ip="10.0.2.10",
                description="srv",
                device_subtype="Linux",
                action_double_click="remote_desktop",
            )
