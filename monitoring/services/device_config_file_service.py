from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil

from monitoring.models.linked_file import LinkedFile
from monitoring.services.config_storage_service import ConfigStorageService, ConfigSyncStats
from monitoring.services.linked_file_service import LinkedFileService


DEVICE_CONFIG_OWNER_KIND = "device"
DEVICE_CONFIG_MODULE_CODE = "monitoring"
DEVICE_CONFIG_CATEGORY = "config"


@dataclass(frozen=True)
class DeviceConfigFile:
    id: str
    name: str
    path: str
    modified_at: str
    detail: str = ""
    size_bytes: int = 0
    sha256: str = ""
    sync_status: str = "local_only"
    sync_error: str = ""
    device_type: str = ""
    device_type_label: str = ""
    device_name: str = ""
    device_ip: str = ""


class DeviceConfigFileService:
    """Facade metier pour les fichiers de configuration des equipements."""

    def __init__(
        self,
        *,
        linked_files: LinkedFileService | None = None,
        config_storage: ConfigStorageService | None = None,
    ) -> None:
        self._linked_files = linked_files or LinkedFileService()
        self._config_storage = config_storage or ConfigStorageService()

    def import_config_file(
        self,
        *,
        device_type: str,
        device_type_label: str,
        device_id: str = "",
        device_name: str,
        device_ip: str = "",
        source_file: Path,
        detail: str = "",
        created_by: str = "",
        stamp_dt: datetime | None = None,
    ) -> DeviceConfigFile:
        src = Path(source_file)
        target_name = self._config_storage.build_import_target_name(
            device_type_label=device_type_label,
            device_name=device_name,
            source_file=src,
            stamp_dt=stamp_dt,
        )
        item = self._linked_files.store_bytes(
            owner_kind=DEVICE_CONFIG_OWNER_KIND,
            owner_id=self._owner_id(device_type=device_type, device_id=device_id, device_name=device_name),
            module_code=DEVICE_CONFIG_MODULE_CODE,
            category=DEVICE_CONFIG_CATEGORY,
            filename=target_name,
            content=src.read_bytes(),
            detail=detail,
            metadata={
                "device_type": str(device_type or "").strip().lower(),
                "device_type_label": str(device_type_label or "").strip(),
                "device_name": str(device_name or "").strip(),
                "device_ip": str(device_ip or "").strip(),
                "source_filename": src.name,
                "source": "manual_import",
            },
            created_by=created_by,
        )
        return self._to_device_config_file(item)

    def list_config_files(
        self,
        *,
        device_type: str,
        device_id: str = "",
        device_name: str,
        limit: int = 200,
    ) -> list[DeviceConfigFile]:
        rows = self._linked_files.list_files(
            owner_kind=DEVICE_CONFIG_OWNER_KIND,
            owner_id=self._owner_id(device_type=device_type, device_id=device_id, device_name=device_name),
            module_code=DEVICE_CONFIG_MODULE_CODE,
            category=DEVICE_CONFIG_CATEGORY,
            limit=limit,
        )
        if str(device_id or "").strip():
            fallback_rows = self._linked_files.list_files(
                owner_kind=DEVICE_CONFIG_OWNER_KIND,
                owner_id=self._owner_id(device_type=device_type, device_name=device_name),
                module_code=DEVICE_CONFIG_MODULE_CODE,
                category=DEVICE_CONFIG_CATEGORY,
                limit=limit,
            )
            seen = {item.id for item in rows}
            rows.extend(item for item in fallback_rows if item.id not in seen)
        return [self._to_device_config_file(item) for item in rows]

    def has_config_files(
        self,
        *,
        device_type: str,
        device_id: str = "",
        device_name: str,
    ) -> bool:
        return bool(
            self.list_config_files(
                device_type=device_type,
                device_id=device_id,
                device_name=device_name,
                limit=1,
            )
        )

    def latest_imported_config_file(
        self,
        *,
        device_type: str,
        device_id: str = "",
        device_name: str,
    ) -> DeviceConfigFile | None:
        rows = self.list_config_files(
            device_type=device_type,
            device_id=device_id,
            device_name=device_name,
            limit=1,
        )
        return rows[0] if rows else None

    def list_all_config_files(self, *, limit: int = 1000) -> list[DeviceConfigFile]:
        rows = self._linked_files.list_files_by_module_category(
            module_code=DEVICE_CONFIG_MODULE_CODE,
            category=DEVICE_CONFIG_CATEGORY,
            limit=limit,
        )
        return [self._to_device_config_file(item) for item in rows]

    def get_config_file(self, file_id: str) -> DeviceConfigFile | None:
        item = self._linked_files.get_file(file_id)
        if item is None:
            return None
        if item.module_code != DEVICE_CONFIG_MODULE_CODE or item.category != DEVICE_CONFIG_CATEGORY:
            return None
        return self._to_device_config_file(item)

    def find_latest_backup_file(
        self,
        *,
        device_name: str,
        device_ip: str,
    ) -> Path | None:
        matches = self._config_storage.find_device_backup_files(
            device_name=device_name,
            device_ip=device_ip,
            max_results=1,
        )
        return Path(matches[0]) if matches else None

    def local_storage_root_dir(self) -> Path:
        return self._linked_files.storage_root_dir()

    def sync_local_versions_to_backup(self, *, backup_root: Path | None = None) -> ConfigSyncStats:
        legacy_stats = (
            self._config_storage.sync_local_versions_to_backup()
            if backup_root is None
            else ConfigSyncStats(scanned=0, copied=0)
        )
        backup_root = Path(backup_root) if backup_root is not None else self._config_storage.backup_root_dir()
        linked_scanned = 0
        linked_copied = 0
        for item in self._linked_files.list_files_by_module_category(
            module_code=DEVICE_CONFIG_MODULE_CODE,
            category=DEVICE_CONFIG_CATEGORY,
        ):
            linked_scanned += 1
            source = Path(item.stored_path)
            if not source.is_file():
                self._linked_files.update_sync_state(item.id, sync_status="failed", sync_error="Fichier local introuvable.")
                continue
            metadata = item.metadata or {}
            type_label = str(metadata.get("device_type_label") or metadata.get("device_type") or "unknown").strip()
            device_name = str(metadata.get("device_name") or item.owner_id or "unknown").strip()
            target = Path(backup_root) / _safe_path_part(type_label) / _safe_path_part(device_name) / item.filename
            try:
                source_stat = source.stat()
                should_copy = True
                if target.is_file():
                    target_stat = target.stat()
                    should_copy = (
                        int(target_stat.st_size) != int(source_stat.st_size)
                        or int(target_stat.st_mtime_ns) != int(source_stat.st_mtime_ns)
                    )
                if should_copy:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    linked_copied += 1
                self._linked_files.update_sync_state(item.id, sync_status="synced", sync_error="")
            except Exception as exc:
                self._linked_files.update_sync_state(item.id, sync_status="failed", sync_error=str(exc))
        return ConfigSyncStats(
            scanned=int(legacy_stats.scanned) + linked_scanned,
            copied=int(legacy_stats.copied) + linked_copied,
        )

    @staticmethod
    def _owner_id(*, device_type: str, device_id: str = "", device_name: str) -> str:
        dtype = str(device_type or "").strip().lower() or "unknown"
        identifier = str(device_id or "").strip() or str(device_name or "").strip() or "unknown"
        return f"{dtype}:{identifier}"

    @staticmethod
    def _to_device_config_file(item: LinkedFile) -> DeviceConfigFile:
        metadata = item.metadata or {}
        return DeviceConfigFile(
            id=item.id,
            name=item.filename,
            path=item.stored_path,
            modified_at=item.updated_at,
            detail=item.detail,
            size_bytes=item.size_bytes,
            sha256=item.sha256,
            sync_status=item.sync_status,
            sync_error=item.sync_error,
            device_type=str(metadata.get("device_type") or ""),
            device_type_label=str(metadata.get("device_type_label") or ""),
            device_name=str(metadata.get("device_name") or ""),
            device_ip=str(metadata.get("device_ip") or ""),
        )


def _safe_path_part(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    cleaned = "".join(ch if ch.isalnum() or ch in {" ", "-", "_", "."} else "_" for ch in raw)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned or "unknown"
