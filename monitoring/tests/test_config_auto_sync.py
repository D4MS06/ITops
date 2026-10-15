from pathlib import Path
from types import SimpleNamespace

from monitoring.api.app import _run_config_storage_auto_sync


class _StorageTargets:
    def __init__(self, mounts):
        self.mounts = mounts

    def describe_remote_mounts(self, *, include_legacy_monitoring):
        assert include_legacy_monitoring is False
        return self.mounts


class _ConfigStorage:
    def __init__(self, root: Path):
        self.root = root
        self.connection_checked = False

    def ensure_backup_connection(self):
        self.connection_checked = True
        return True, "Connecte"

    def backup_root_dir(self):
        return self.root


class _DeviceConfigFiles:
    def __init__(self):
        self.roots = []

    def sync_local_versions_to_backup(self, *, backup_root):
        self.roots.append(Path(backup_root))
        return SimpleNamespace(scanned=4, copied=2)


def _services(*, enabled=True, mode="smb3", mounts=(), root=Path("fallback")):
    return SimpleNamespace(
        settings_service=SimpleNamespace(get=lambda: SimpleNamespace(
            config_auto_sync_enabled=enabled,
            config_storage_mode=mode,
        )),
        storage_targets=_StorageTargets(mounts),
        config_storage=_ConfigStorage(root),
        device_config_files=_DeviceConfigFiles(),
    )


def test_auto_sync_uses_active_network_equipment_storage_target(tmp_path: Path):
    target = tmp_path / "network-config-backup"
    services = _services(mounts=[{
        "service_code": "network_equipment.device_config_files",
        "automount_active": True,
        "target_path": str(target),
    }])

    completed, message = _run_config_storage_auto_sync(services)

    assert completed is True
    assert "analysees: 4" in message
    assert services.device_config_files.roots == [target]
    assert services.config_storage.connection_checked is False


def test_auto_sync_falls_back_to_legacy_smb_configuration(tmp_path: Path):
    target = tmp_path / "legacy-backup"
    services = _services(root=target)

    completed, _message = _run_config_storage_auto_sync(services)

    assert completed is True
    assert services.config_storage.connection_checked is True
    assert services.device_config_files.roots == [target]


def test_auto_sync_does_not_run_when_disabled():
    services = _services(enabled=False)

    completed, message = _run_config_storage_auto_sync(services)

    assert completed is False
    assert "desactivee" in message
    assert services.device_config_files.roots == []
