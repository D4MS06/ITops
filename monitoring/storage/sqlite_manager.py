from __future__ import annotations

import os
import sqlite3
import threading
from typing import Dict, List

from monitoring.repositories.sqlite_repositories import (
    ConfigVersionRepository,
    DeviceRepository,
    DeviceTypeRepository,
    StatusLogRepository,
)
from monitoring.storage.sqlite_auth_sessions import AuthSessionRepository
from monitoring.storage.sqlite_bootstrap import SQLiteBootstrapper
from monitoring.utils.logger import log_with_timestamp


class SQLiteFileManager:
    _lock = threading.Lock()
    OS_FIELD_OPTIONS = "Windows,Linux,Firmware,Autre"
    OS_FIELD_DEFAULT = "Windows"
    ALL_OS_SCOPE = "windows,linux,firmware,autre"

    @staticmethod
    def _normalize_os_key(value: str) -> str:
        raw = str(value or "").strip().lower()
        return raw if raw in {"windows", "linux", "firmware", "autre"} else "autre"

    @staticmethod
    def _format_os_scope(values: list[str]) -> str:
        ordered = []
        seen: set[str] = set()
        for value in values:
            key = SQLiteFileManager._normalize_os_key(value)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(key)
        return ",".join(ordered)

    def __init__(self, db_name: str = "devices.db") -> None:
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        self.data_dir = os.path.join(local_app_data, "NetworkMonitoringProject", "data")
        self.db_path = os.path.join(self.data_dir, db_name)
        self._init_repositories()

    def _init_repositories(self) -> None:
        self.devices = DeviceRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.device_types = DeviceTypeRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.status_logs = StatusLogRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.config_versions = ConfigVersionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )
        self.auth_sessions = AuthSessionRepository(
            connect=self._connect,
            ensure_database=self._ensure_database,
            lock=SQLiteFileManager._lock,
        )

    def _ensure_repositories(self) -> None:
        if not all(hasattr(self, attr) for attr in ("devices", "device_types", "status_logs", "config_versions", "auth_sessions")):
            self._init_repositories()

    def _repo(self, attr: str):
        self._ensure_repositories()
        return getattr(self, attr)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_database(self) -> None:
        SQLiteBootstrapper.ensure_database(self)

    @staticmethod
    def _ensure_status_logs_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_status_logs_columns(conn)

    @staticmethod
    def _ensure_devices_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_devices_columns(conn)

    @staticmethod
    def _ensure_device_type_actions_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_device_type_actions_columns(conn)

    @staticmethod
    def _ensure_device_types_columns(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_device_types_columns(conn)

    @staticmethod
    def _ensure_default_schema_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_default_schema_rows(conn, SQLiteFileManager)

    def _seed_from_json(self, conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.seed_from_json(conn)

    @staticmethod
    def _seed_default_device_types(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.seed_default_device_types(conn, SQLiteFileManager)

    @staticmethod
    def _ensure_os_field_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_os_field_rows(conn, SQLiteFileManager)

    @staticmethod
    def _ensure_action_os_scope_rows(conn: sqlite3.Connection) -> None:
        SQLiteBootstrapper.ensure_action_os_scope_rows(conn, SQLiteFileManager)

    def read_devices_map(self) -> Dict[str, List[dict]]:
        return self._repo("devices").read_devices_map()

    def list_device_types(self) -> List[dict]:
        return self._repo("device_types").list_device_types()

    def list_type_fields(self, type_code: str) -> List[dict]:
        return self._repo("device_types").list_type_fields(type_code)

    def list_type_actions(self, type_code: str) -> List[dict]:
        return self._repo("device_types").list_type_actions(type_code)

    def save_device_type(
        self,
        *,
        code: str,
        label: str,
        template_code: str | None = None,
        monitoring_enabled: bool = True,
        config_backups_enabled: bool | None = None,
        rebuild_schema: bool = False,
    ) -> str:
        return self._repo("device_types").save_device_type(
            code=code,
            label=label,
            template_code=template_code,
            monitoring_enabled=monitoring_enabled,
            config_backups_enabled=config_backups_enabled,
            rebuild_schema=rebuild_schema,
        )

    def count_devices_by_type(self, code: str) -> int:
        return self._repo("device_types").count_devices_by_type(code)

    def delete_device_type(self, code: str, *, cascade_devices: bool = False) -> bool:
        return self._repo("device_types").delete_device_type(code, cascade_devices=cascade_devices)

    def replace_type_schema(
        self,
        *,
        type_code: str,
        fields: List[dict],
        actions: List[dict],
    ) -> None:
        self._repo("device_types").replace_type_schema(type_code=type_code, fields=fields, actions=actions)

    def record_status_log(
        self,
        *,
        dtype: str,
        device_id: str,
        device_name: str,
        old_status: str,
        new_status: str,
        event_kind: str = "status_change",
        details: str = "",
    ) -> None:
        self._repo("status_logs").record_status_log(
            dtype=dtype,
            device_id=device_id,
            device_name=device_name,
            old_status=old_status,
            new_status=new_status,
            event_kind=event_kind,
            details=details,
        )

    def list_status_logs(
        self,
        *,
        limit: int = 300,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> List[dict]:
        return self._repo("status_logs").list_status_logs(limit=limit, dtype=dtype, device_id=device_id)

    def delete_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        return self._repo("status_logs").delete_status_logs(dtype=dtype, device_id=device_id)

    def count_status_logs(
        self,
        *,
        dtype: str | None = None,
        device_id: str | None = None,
    ) -> int:
        return self._repo("status_logs").count_status_logs(dtype=dtype, device_id=device_id)

    def upsert_config_file_version(
        self,
        *,
        file_path: str,
        device_type_label: str,
        device_name: str,
        filename: str,
        detail: str = "",
    ) -> None:
        self._repo("config_versions").upsert_config_file_version(
            file_path=file_path,
            device_type_label=device_type_label,
            device_name=device_name,
            filename=filename,
            detail=detail,
        )

    def list_config_file_versions(
        self,
        *,
        device_type_label: str,
        device_name: str,
    ) -> List[dict]:
        return self._repo("config_versions").list_config_file_versions(
            device_type_label=device_type_label,
            device_name=device_name,
        )

    def delete_config_file_version(self, *, file_path: str) -> int:
        return self._repo("config_versions").delete_config_file_version(file_path=file_path)

    def rename_config_file_version(self, *, old_file_path: str, new_file_path: str, new_filename: str) -> int:
        return self._repo("config_versions").rename_config_file_version(
            old_file_path=old_file_path,
            new_file_path=new_file_path,
            new_filename=new_filename,
        )

    def delete_config_file_versions_by_type_label(self, *, device_type_label: str) -> int:
        return self._repo("config_versions").delete_config_file_versions_by_type_label(
            device_type_label=device_type_label
        )

    def upsert_device(self, *, dtype: str, item: dict) -> None:
        self._repo("devices").upsert_device(dtype=dtype, item=item)

    def delete_device(self, *, device_id: str) -> int:
        return self._repo("devices").delete_device(device_id=device_id)

    def write_devices_map(self, data: Dict[str, List[dict]]) -> None:
        self._repo("devices").write_devices_map(data)
        total = sum(len(items) for items in data.values())
        log_with_timestamp(f"Ecriture SQLite reussie ({total} equipements).", level="DEBUG")

    def save_auth_session(self, *, token: str, subject: str, created_at: str, expires_at: str) -> None:
        self._repo("auth_sessions").save_auth_session(
            token=token,
            subject=subject,
            created_at=created_at,
            expires_at=expires_at,
        )

    def get_auth_session(self, *, token: str) -> dict | None:
        return self._repo("auth_sessions").get_auth_session(token=token)

    def delete_auth_session(self, *, token: str) -> int:
        return self._repo("auth_sessions").delete_auth_session(token=token)

    def delete_all_auth_sessions(self) -> int:
        return self._repo("auth_sessions").delete_all_auth_sessions()

    def delete_expired_auth_sessions(self, *, now_iso: str) -> int:
        return self._repo("auth_sessions").delete_expired_auth_sessions(now_iso=now_iso)
