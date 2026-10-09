from __future__ import annotations

from datetime import datetime
from pathlib import Path

from monitoring.services.device_config_file_service import DeviceConfigFileService
from monitoring.services.linked_file_service import LinkedFileService
from monitoring.tests.test_linked_file_service import _FakeLinkedFileManager


class _FakeConfigStorage:
    def __init__(self, backup_matches: list[Path] | None = None, backup_root: Path | None = None) -> None:
        self.backup_matches = backup_matches or []
        self.backup_root = backup_root or Path(".")
        self.synced = False

    def build_import_target_name(self, *, device_type_label, device_name, source_file, stamp_dt=None):
        stamp = (stamp_dt or datetime(2026, 6, 17, 10, 30, 0)).strftime("%Y-%m-%d_%H-%M-%S")
        return f"{device_type_label}_{device_name}_{stamp}{Path(source_file).suffix or '.cfg'}"

    def find_device_backup_files(self, *, device_name, device_ip, max_results=20):
        return self.backup_matches[:max_results]

    def sync_local_versions_to_backup(self):
        self.synced = True
        return type("Stats", (), {"scanned": 2, "copied": 1})()

    def backup_root_dir(self):
        return self.backup_root


def test_device_config_file_service_imports_device_config_with_inventory_metadata(tmp_path: Path):
    source = tmp_path / "startup.cfg"
    source.write_text("hostname SW-CORE-01\n", encoding="utf-8")
    manager = _FakeLinkedFileManager()
    linked_files = LinkedFileService(manager, storage_root_provider=lambda: tmp_path / "linked")
    service = DeviceConfigFileService(
        linked_files=linked_files,
        config_storage=_FakeConfigStorage(),
    )

    item = service.import_config_file(
        device_type="switch",
        device_type_label="Switch",
        device_id="sw-core-01",
        device_name="SW-CORE-01",
        device_ip="192.0.2.10",
        source_file=source,
        detail="Avant mise a jour firmware",
        created_by="tech",
        stamp_dt=datetime(2026, 6, 17, 10, 30, 0),
    )

    assert item.name == "Switch_SW-CORE-01_2026-06-17_10-30-00.cfg"
    assert item.detail == "Avant mise a jour firmware"
    assert item.size_bytes == len(source.read_bytes())
    assert Path(item.path).read_bytes() == source.read_bytes()

    rows = service.list_config_files(device_type="switch", device_id="sw-core-01", device_name="SW-CORE-01")
    assert rows == [item]
    assert service.list_all_config_files() == [item]
    assert service.get_config_file(item.id) == item
    assert item.device_type == "switch"
    assert item.device_type_label == "Switch"
    assert item.device_name == "SW-CORE-01"
    assert item.device_ip == "192.0.2.10"
    assert service.has_config_files(device_type="switch", device_id="sw-core-01", device_name="SW-CORE-01") is True


def test_device_config_file_service_ignores_missing_physical_files(tmp_path: Path):
    source = tmp_path / "startup.cfg"
    source.write_text("hostname SW-CORE-01\n", encoding="utf-8")
    manager = _FakeLinkedFileManager()
    linked_files = LinkedFileService(manager, storage_root_provider=lambda: tmp_path / "linked")
    service = DeviceConfigFileService(
        linked_files=linked_files,
        config_storage=_FakeConfigStorage(),
    )
    item = service.import_config_file(
        device_type="switch",
        device_type_label="Switch",
        device_id="sw-core-01",
        device_name="SW-CORE-01",
        device_ip="192.0.2.10",
        source_file=source,
    )
    Path(item.path).unlink()

    assert service.list_config_files(device_type="switch", device_id="sw-core-01", device_name="SW-CORE-01") == []
    assert service.list_all_config_files() == []
    assert service.get_config_file(item.id) is None
    assert service.latest_imported_config_file(device_type="switch", device_id="sw-core-01", device_name="SW-CORE-01") is None
    assert service.has_config_files(device_type="switch", device_id="sw-core-01", device_name="SW-CORE-01") is False
    assert service.delete_config_file(item.id, delete_physical_file=True) is True


def test_device_config_file_service_keeps_backup_lookup_and_sync_delegated(tmp_path: Path):
    backup = tmp_path / "SW-CORE-01_192.0.2.10.cfg"
    backup.write_text("backup", encoding="utf-8")
    config_storage = _FakeConfigStorage(backup_matches=[backup], backup_root=tmp_path / "remote")
    service = DeviceConfigFileService(
        linked_files=LinkedFileService(_FakeLinkedFileManager(), storage_root_provider=lambda: tmp_path / "linked"),
        config_storage=config_storage,
    )

    assert service.find_latest_backup_file(device_name="SW-CORE-01", device_ip="192.0.2.10") == backup
    stats = service.sync_local_versions_to_backup()
    assert stats.scanned == 2
    assert stats.copied == 1
    assert config_storage.synced is True


def test_device_config_file_service_syncs_linked_config_files_to_backup(tmp_path: Path):
    source = tmp_path / "startup.cfg"
    source.write_text("hostname SW-CORE-01\n", encoding="utf-8")
    manager = _FakeLinkedFileManager()
    linked_files = LinkedFileService(manager, storage_root_provider=lambda: tmp_path / "linked")
    config_storage = _FakeConfigStorage(backup_root=tmp_path / "remote")
    service = DeviceConfigFileService(linked_files=linked_files, config_storage=config_storage)
    item = service.import_config_file(
        device_type="switch",
        device_type_label="Switch",
        device_id="sw-core-01",
        device_name="SW-CORE-01",
        device_ip="192.0.2.10",
        source_file=source,
    )

    stats = service.sync_local_versions_to_backup()

    copied = tmp_path / "remote" / "Switch" / "SW-CORE-01" / item.name
    assert copied.read_bytes() == source.read_bytes()
    assert stats.scanned == 3
    assert stats.copied == 2
    assert manager.rows[item.id]["sync_status"] == "synced"
