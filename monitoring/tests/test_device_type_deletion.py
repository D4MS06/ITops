from __future__ import annotations

from pathlib import Path

from monitoring.services.device_type_service import DeviceTypeService


class _Manager:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, bool]] = []
        self.deleted_config_labels: list[str] = []
        self.delete_result = True

    def list_device_types(self):
        return [{"code": "printer", "label": "Imprimantes"}]

    def read_devices_map(self):
        return {
            "printer": [
                {"id": "printer-1", "name": "Imprimante accueil"},
                {"id": "printer-2", "name": "Imprimante direction"},
            ]
        }

    def delete_device_type(self, code: str, *, cascade_devices: bool = False):
        self.deleted.append((code, cascade_devices))
        return self.delete_result

    def delete_config_file_versions_by_type_label(self, *, device_type_label: str):
        self.deleted_config_labels.append(device_type_label)


class _ConfigStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def local_versions_root_dir(self):
        return self.root / "local"

    def backup_root_dir(self):
        return self.root / "backup"


class _DeviceService:
    def __init__(self) -> None:
        self.deleted_credentials: list[tuple[str, str]] = []

    def delete_vault_credentials(self, *, dtype: str, device_id: str):
        self.deleted_credentials.append((dtype, device_id))


class _DeviceConfigFiles:
    def __init__(self) -> None:
        self.deleted_devices: list[tuple[str, str, str]] = []

    def delete_config_files_for_device(self, *, device_type: str, device_id: str, device_name: str):
        self.deleted_devices.append((device_type, device_id, device_name))
        return 1


def test_delete_type_with_cascade_cleans_device_artifacts(tmp_path: Path):
    manager = _Manager()
    device_service = _DeviceService()
    config_files = _DeviceConfigFiles()
    service = DeviceTypeService(
        manager,
        config_storage=_ConfigStorage(tmp_path),
        device_service=device_service,
        device_config_files=config_files,
    )

    assert service.delete_type("Printer", cascade_devices=True) is True

    assert manager.deleted == [("printer", True)]
    assert device_service.deleted_credentials == [("printer", "printer-1"), ("printer", "printer-2")]
    assert config_files.deleted_devices == [
        ("printer", "printer-1", "Imprimante accueil"),
        ("printer", "printer-2", "Imprimante direction"),
    ]
    assert manager.deleted_config_labels == ["Imprimantes"]


def test_delete_type_does_not_clean_artifacts_when_database_deletion_fails(tmp_path: Path):
    manager = _Manager()
    manager.delete_result = False
    device_service = _DeviceService()
    config_files = _DeviceConfigFiles()
    service = DeviceTypeService(
        manager,
        config_storage=_ConfigStorage(tmp_path),
        device_service=device_service,
        device_config_files=config_files,
    )

    assert service.delete_type("printer", cascade_devices=True) is False

    assert device_service.deleted_credentials == []
    assert config_files.deleted_devices == []
    assert manager.deleted_config_labels == []
