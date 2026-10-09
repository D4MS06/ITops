from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from monitoring.config.settings import NotificationSettings, load_settings
from monitoring.services.device_config_storage_contract import NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE
from monitoring.utils.config_files import (
    build_device_config_filename,
    default_local_config_versions_dir,
    describe_config_remote_mount,
    ensure_smb3_connection,
    file_creation_datetime,
    find_switch_config_files,
    resolve_config_backup_dir,
    resolve_local_type_versions_dir,
    store_imported_config_version,
    sync_local_versions_to_backup,
)


@dataclass(frozen=True)
class ConfigSyncStats:
    scanned: int
    copied: int


class ConfigStorageService:
    def __init__(
        self,
        *,
        settings_provider: Callable[[], NotificationSettings] | None = None,
    ) -> None:
        self._settings_provider = settings_provider or load_settings

    def settings(self) -> NotificationSettings:
        return self._settings_provider()

    def backup_root_dir(self) -> Path:
        return resolve_config_backup_dir(self.settings())

    def ensure_backup_connection(self) -> tuple[bool, str]:
        return ensure_smb3_connection(self.settings())

    def remote_mount_descriptors(self) -> list[dict[str, object]]:
        return [
            describe_config_remote_mount(
                self.settings(),
                service_code=NETWORK_EQUIPMENT_CONFIG_STORAGE_SERVICE_CODE,
                service_label="Équipements réseau - fichiers de configuration",
            )
        ]

    def local_versions_root_dir(self) -> Path:
        return default_local_config_versions_dir()

    def local_versions_dir_for_type(self, device_type: str) -> Path:
        return resolve_local_type_versions_dir(device_type=device_type)

    def find_device_backup_files(
        self,
        *,
        device_name: str,
        device_ip: str,
        max_results: int = 20,
    ) -> list[Path]:
        return find_switch_config_files(
            self.backup_root_dir(),
            str(device_name or ""),
            str(device_ip or ""),
            max_results=max_results,
        )

    def has_device_backup(self, *, device_name: str, device_ip: str) -> bool:
        return bool(
            self.find_device_backup_files(
                device_name=device_name,
                device_ip=device_ip,
                max_results=1,
            )
        )

    def download_latest_device_backup(
        self,
        *,
        device_name: str,
        device_ip: str,
        target_path: Path,
    ) -> Path:
        matches = self.find_device_backup_files(
            device_name=device_name,
            device_ip=device_ip,
            max_results=1,
        )
        if not matches:
            raise FileNotFoundError("Aucune sauvegarde correspondante.")
        source = matches[0]
        destination = Path(target_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def build_import_target_name(
        self,
        *,
        device_type_label: str,
        device_name: str,
        source_file: Path,
        stamp_dt=None,
    ) -> str:
        return build_device_config_filename(
            device_type_label=device_type_label,
            device_name=device_name,
            source_file=Path(source_file),
            stamp_dt=stamp_dt,
        )

    def import_device_config_version(
        self,
        *,
        device_type_label: str,
        device_name: str,
        source_file: Path,
        detail: str = "",
        stamp_dt=None,
    ) -> Path:
        return store_imported_config_version(
            local_versions_root=self.local_versions_root_dir(),
            device_type_label=device_type_label,
            device_name=device_name,
            source_file=Path(source_file),
            detail=detail,
            stamp_dt=stamp_dt,
        )

    def file_created_at(self, source_file: Path):
        return file_creation_datetime(Path(source_file))

    def sync_local_versions_to_backup(self) -> ConfigSyncStats:
        stats = sync_local_versions_to_backup(
            local_versions_root=self.local_versions_root_dir(),
            backup_root=self.backup_root_dir(),
        )
        return ConfigSyncStats(
            scanned=int(stats.get("scanned", 0)),
            copied=int(stats.get("copied", 0)),
        )
